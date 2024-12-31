import easyocr
import re
from PIL import Image, ImageEnhance
import os
import numpy as np
import cv2

class OCRProcessor:
    def __init__(self, mode='auto'):
        """
        初始化OCR处理器
        Args:
            mode: 'auto', 'printed' 或 'handwritten'
        """
        self.mode = mode
        print("正在初始化EasyOCR，首次运行需要下载模型，请稍候...")
        
        # 初始化 EasyOCR
        self.reader = easyocr.Reader(
            ['ch_sim', 'en'],
            gpu=False,
            model_storage_directory=os.path.join(os.path.expanduser('~'), '.EasyOCR')
        )
        
        print("EasyOCR初始化完成！")
        
        # 配置参数
        self.config = {
            # OCR参数
            'number_confidence': 0.2 if mode == 'handwritten' else 0.3,  # 降低数字的置信度阈值
            'text_confidence': 0.1 if mode == 'handwritten' else 0.2,    # 降低文本的置信度阈值
            
            # 图片预处理参数
            'max_size': 1500 if mode == 'handwritten' else 1000,
            'contrast_enhance': 1.5,
            'preprocessing': {
                'enable': True,
                'denoise': True,
                'threshold': True,
                'deskew': True,
                'kernel_size': 3,
                'block_size': 11
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
            # 使用EasyOCR进行识别
            results = self.reader.readtext(
                processed_image,
                detail=1,
                paragraph=False,
                contrast_ths=0.2,
                adjust_contrast=0.8
            )
            
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
            
            # 调整大小
            ratio = min(self.config['max_size'] / image.width, 
                       self.config['max_size'] / image.height)
            if ratio < 1:
                new_size = (int(image.width * ratio), int(image.height * ratio))
                gray_image = gray_image.resize(new_size, Image.Resampling.LANCZOS)
                print(f"图片已调整大小至: {new_size}")
            
            # 增强对比度
            enhanced_image = ImageEnhance.Contrast(gray_image).enhance(
                self.config['contrast_enhance']
            )
            
            # 转换为numpy数组
            img_array = np.array(enhanced_image)
            
            if self.mode == 'handwritten':
                # 降噪
                if self.config['preprocessing']['denoise']:
                    img_array = cv2.fastNlMeansDenoising(img_array)
                
                # 自适应二值化
                if self.config['preprocessing']['threshold']:
                    img_array = cv2.adaptiveThreshold(
                        img_array,
                        255,
                        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                        cv2.THRESH_BINARY,
                        self.config['preprocessing']['block_size'],
                        2
                    )
            
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

# 用于直接测试
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        processor = OCRProcessor(mode='auto')
        processor.test_file(sys.argv[1]) 