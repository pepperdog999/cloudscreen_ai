# OCR API 服务

这是一个基于 FastAPI 的 OCR 服务，主要用于识别中文手写内容的图片，并将识别结果转换为结构化的 JSON 数据。

## 功能特性

- 支持中文手写内容识别
- 自动识别文本中的时间信息
- 按行返回识别结果
- 提供测试接口和 OCR 处理接口

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

1. 启动服务：
```bash
python main.py
```

2. 访问接口：
- 测试接口：GET http://localhost:8000/test
- OCR处理接口：POST http://localhost:8000/ocr

3. OCR接口使用说明：
- 请求方式：POST
- 接口地址：http://localhost:8000/ocr
- 参数：file (图片文件)
- 返回格式：
```json
{
    "code": 200,
    "message": "success",
    "data": [
        {
            "start_time": "00:00:00",
            "end_time": "00:00:00",
            "content": "识别的文本内容"
        }
    ]
}
```

## 注意事项

1. 图片要求：
   - 支持常见图片格式（jpg、png等）
   - 图片清晰度要求较高
   - 建议图片大小不超过 5MB

2. 性能说明：
   - 首次启动时需要下载模型文件
   - 单次识别时间约 1-3 秒
