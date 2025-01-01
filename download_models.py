import easyocr
import shutil
import os
from pathlib import Path

def download_models():
    print("开始下载模型文件...")
    
    # 初始化 EasyOCR，这会自动下载模型
    reader = easyocr.Reader(['ch_sim','en'], verbose=True)
    
    # 获取模型文件路径
    home_dir = str(Path.home())
    model_dir = os.path.join(home_dir, '.EasyOCR')
    
    # 打印原始模型文件列表
    print("\n原始模型文件列表:")
    for root, dirs, files in os.walk(model_dir):
        for file in files:
            file_path = os.path.join(root, file)
            file_size = os.path.getsize(file_path) / (1024 * 1024)  # 转换为MB
            print(f"{file_path}: {file_size:.2f}MB")
    
    # 创建模型存储目录
    if not os.path.exists('models'):
        os.makedirs('models')
    
    # 复制模型文件到本地目录
    print(f"\n复制模型文件从 {model_dir} 到 ./models")
    shutil.copytree(model_dir, './models/EasyOCR', dirs_exist_ok=True)
    
    # 验证复制的文件
    print("\n复制后的模型文件列表:")
    copied_model_dir = './models/EasyOCR'
    for root, dirs, files in os.walk(copied_model_dir):
        for file in files:
            file_path = os.path.join(root, file)
            file_size = os.path.getsize(file_path) / (1024 * 1024)  # 转换为MB
            print(f"{file_path}: {file_size:.2f}MB")
    
    print("\n模型文件下载和复制完成！")

if __name__ == "__main__":
    download_models() 