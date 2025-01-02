import easyocr
import re
from PIL import Image, ImageEnhance
import os
import numpy as np
import cv2
from pathlib import Path

class OCRProcessor:
    def __init__(self, mode='auto'):
        """
        初始化OCR处理器
        Args:
            mode: 'auto', 'printed' 或 'handwritten'
        """
        self.mode = mode
        print("正在初始化EasyOCR...")
        
        # 设置模型目录
        model_dir = Path('./models/EasyOCR/model')
        if not model_dir.exists():
            raise Exception("模型目录不存在，请先运行 download_models.py 下载模型文件")
        
        # 初始化 EasyOCR，使用本地模型
        self.reader = easyocr.Reader(
            ['ch_sim', 'en'],
            gpu=False,
            model_storage_directory=str(model_dir),
            download_enabled=False  # 禁用自动下载
        )
        
        print("EasyOCR初始化完成！")
        
        # 配置参数
        self.config = {
            # OCR参数 - 手写体使用更宽松的阈值
            'number_confidence': 0.1 if mode == 'handwritten' else 0.3,  # 更低的数字置信度阈值
            'text_confidence': 0.1 if mode == 'handwritten' else 0.2,    # 更低的文本置信度阈值
            
            # 图片预处理参数
            'max_size': 2000 if mode == 'handwritten' else 1000,  # 更高的分辨率
            'contrast_enhance': 2.0 if mode == 'handwritten' else 1.5,  # 更强的对比度增强
            'preprocessing': {
                'enable': True,
                'denoise': True,
                'threshold': True,
                'deskew': True,
                'kernel_size': 2,      # 更小的核大小，保留更多细节
                'block_size': 11,
                'clahe': True,         # 启用自适应直方图均衡化
                'sharpen': True,       # 启用锐化
                'morphology': True     # 启用形态学操作
            }
        }

    def process_image(self, image):
        """
        处理图片的OCR识别
        """
        try:
            # 图片预处理
            processed_image = self.preprocess_image(image)
            
            print("开始OCR识别...")
            # 第一次尝试 - 原始图像
            results = self.reader.readtext(
                processed_image,
                detail=1,
                paragraph=False,
                contrast_ths=0.2,
                adjust_contrast=0.8
            )
            
            # 如果识别结果不理想，尝试不同的预处理
            if not results or len(results) < 2:
                print("首次识别结果不理想，尝试其他预处理方法...")
                
                # 尝试反色图像
                inverted_image = cv2.bitwise_not(processed_image)
                results_inv = self.reader.readtext(
                    inverted_image,
                    detail=1,
                    paragraph=False,
                    contrast_ths=0.1,  # 降低对比度阈值
                    adjust_contrast=1.5 # 增加对比度调整
                )
                
                # 使用效果更好的结果
                if len(results_inv) > len(results):
                    results = results_inv
            
            if not results:
                print("未识别到文本")
                return []
            
            # 打印原始识别结果
            print("\n原始识别结果:")
            formatted_results = []
            for bbox, text, conf in results:
                print(f"文本: {text}, 置信度: {conf:.2f}")
                # 根据文本类型选择置信度阈值
                is_time = bool(re.search(r'\d', text))
                threshold = (self.config['number_confidence'] 
                           if is_time 
                           else self.config['text_confidence'])
                if conf >= threshold:
                    formatted_results.append((bbox, text, conf))
            
            # 合并相邻的时间和内容
            merged_lines = []
            current_line_texts = []
            last_y = None
            y_threshold = 10  # 垂直距离阈值，用于判断是否是同一行
            
            # 先按y坐标分组，再按x坐标排序
            formatted_results.sort(key=lambda x: x[0][0][1])  # 先按y排序
            
            for bbox, text, conf in formatted_results:
                current_y = bbox[0][1]  # 当前文本的y坐标
                
                # 如果是同一行（y坐标接近）
                if last_y is not None and abs(current_y - last_y) < y_threshold:
                    current_line_texts.append((bbox[0][0], text.strip()))  # 保存x坐标和文本
                else:
                    # 处理上一行
                    if current_line_texts:
                        # 按x坐标排序当前行的文本
                        current_line_texts.sort(key=lambda x: x[0])
                        # 合并文本
                        merged_line = " ".join(text for _, text in current_line_texts)
                        merged_lines.append(merged_line)
                    # 开始新的一行
                    current_line_texts = [(bbox[0][0], text.strip())]
                
                last_y = current_y
            
            # 处理最后一行
            if current_line_texts:
                current_line_texts.sort(key=lambda x: x[0])
                merged_line = " ".join(text for _, text in current_line_texts)
                merged_lines.append(merged_line)
            
            print("\n合并后的行:")
            for line in merged_lines:
                print(f"行内容: {line}")
            
            # 处理每一行
            processed_texts = []
            for line in merged_lines:
                try:
                    # 先尝试匹配时间段格式
                    time_range_pattern = r'(\d{1,2}[:：]?\d{1,2})[.。\s~～\-—_至到]+(\d{1,2}[:：]?\d{1,2})'
                    # 单时间格式
                    single_time_pattern = r'(\d{1,2}[:：]?\d{1,2})'
                    
                    time_range_match = re.search(time_range_pattern, line)
                    single_time_match = re.search(single_time_pattern, line)
                    
                    # 标准化时间格式
                    def normalize_time(t):
                        if ':' not in t and '：' not in t:
                            if len(t) <= 2:
                                return f"{t.zfill(2)}:00:00"
                            return f"{t[:2]}:{t[2:]}:00"
                        t = t.replace('：', ':')
                        parts = t.split(':')
                        if len(parts) == 2:
                            hour, minute = parts
                            # 验证时间格式的合法性
                            hour = int(hour)
                            minute = int(minute)
                            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                                raise ValueError(f"无效的时间格式: {t}")
                            return f"{hour:02d}:{minute:02d}:00"
                        return t
                    
                    # 提取时间和内容
                    if time_range_match:  # 如果是时间段格式
                        start_time = normalize_time(time_range_match.group(1))
                        end_time = normalize_time(time_range_match.group(2))
                        content = line[time_range_match.end():].strip()
                    elif single_time_match:  # 如果是单时间格式
                        start_time = normalize_time(single_time_match.group(1))
                        end_time = start_time  # 开始时间等于结束时间
                        content = line[single_time_match.end():].strip()
                    else:
                        print(f"跳过非时间格式行: {line}")
                        continue
                    
                    # 清理内容文本
                    content = re.sub(r'[^\u4e00-\u9fff\w]+', '', content)  # 只保留中文、数字和字母
                    
                    # 只有当同时有时间和内容时才添加记录
                    if content:
                        record = {
                            "start_time": start_time,
                            "end_time": end_time,
                            "content": content
                        }
                        processed_texts.append(record)
                        print(f"添加有效记录: {start_time} - {end_time} {content}")
                    else:
                        print(f"跳过无内容的时间行: {line}")
                    
                except ValueError as ve:
                    print(f"时间格式错误: {str(ve)}")
                    continue
                except Exception as e:
                    print(f"处理行时出错: {str(e)}")
                    continue
            
            if not processed_texts:
                print("未能识别到有效的时间和内容")
            else:
                print(f"\n成功识别 {len(processed_texts)} 条有效记录")
            
            return processed_texts
            
        except Exception as e:
            print(f"处理错误: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return []

    def preprocess_image(self, image):
        """
        图片预处理
        """
        try:
            if isinstance(image, np.ndarray):
                image = Image.fromarray(image)
            
            # 转换为灰度图像
            gray_image = image.convert('L')
            
            if not self.config['preprocessing']['enable']:
                return np.array(gray_image)
            
            # 调整大小，但保持较高分辨率
            max_size = 2000 if self.mode == 'handwritten' else 1000  # 手写体使用更高分辨率
            ratio = min(max_size / image.width, max_size / image.height)
            if ratio < 1:
                new_size = (int(image.width * ratio), int(image.height * ratio))
                gray_image = gray_image.resize(new_size, Image.Resampling.LANCZOS)
            
            # 转换为numpy数组
            img_array = np.array(gray_image)
            
            if self.mode == 'handwritten':
                # 自适应直方图均衡化
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
                img_array = clahe.apply(img_array)
                
                # 降噪
                img_array = cv2.fastNlMeansDenoising(img_array, None, h=10, templateWindowSize=7, searchWindowSize=21)
                
                # 锐化
                kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
                img_array = cv2.filter2D(img_array, -1, kernel)
                
                # 自适应二值化
                img_array = cv2.adaptiveThreshold(
                    img_array,
                    255,
                    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                    cv2.THRESH_BINARY,
                    11,  # 块大小
                    2    # 常数
                )
                
                # 形态学操作
                kernel = np.ones((2,2), np.uint8)
                img_array = cv2.morphologyEx(img_array, cv2.MORPH_CLOSE, kernel)  # 闭运算，连接断开的笔画
                
                # 倾斜校正
                coords = np.column_stack(np.where(img_array > 0))
                angle = cv2.minAreaRect(coords)[-1]
                if angle < -45:
                    angle = 90 + angle
                (h, w) = img_array.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                img_array = cv2.warpAffine(img_array, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
            
            return img_array
            
        except Exception as e:
            print(f"图片预处理错误: {str(e)}")
            return np.array(gray_image)

    def test_file(self, image_path: str):
        """
        测试函数：直接使用本地图片文件进行OCR测试
        """
        try:
            if not os.path.exists(image_path):
                raise Exception(f"文件不存在: {image_path}")
            
            # 读取图片
            print(f"正在读取图片: {image_path}")
            image = Image.open(image_path)
            
            # 处理图片
            result = self.process_image(image)
            
            print("\nOCR识别结果:")
            for item in result:
                print(f"时间: {item['start_time']} - {item['end_time']}")
                print(f"内容: {item['content']}")
                print("-" * 50)
                
            return result
            
        except Exception as e:
            print(f"测试过程出错: {str(e)}")
            return None

    def validate_and_correct_time(self, time_str):
        """验证并修正时间格式"""
        try:
            # 常见错误修正
            corrections = {
                'l': '1',
                'o': '0',
                'O': '0',
                'i': '1',
                'I': '1',
                'z': '2',
                'Z': '2',
                'S': '5',
                'B': '8',
            }
            
            for wrong, correct in corrections.items():
                time_str = time_str.replace(wrong, correct)
            
            # 验证时间格式
            if ':' not in time_str and '：' not in time_str:
                # 处理无分隔符的情况
                if len(time_str) == 3:
                    time_str = f"{time_str[0]}:{time_str[1:3]}"
                elif len(time_str) == 4:
                    time_str = f"{time_str[:2]}:{time_str[2:]}"
            
            return time_str
        except:
            return time_str

# 用于直接测试
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        processor = OCRProcessor(mode='auto')
        processor.test_file(sys.argv[1]) 