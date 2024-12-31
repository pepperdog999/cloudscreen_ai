from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from PIL import Image
import io
from ocr import OCRProcessor

app = FastAPI(title="OCR API Service")

# 初始化OCR处理器
ocr_processor = OCRProcessor()

# 基础响应模型
def create_response(code: int = 200, message: str = "success", data: any = None):
    return {
        "code": code,
        "message": message,
        "data": data
    }

# 测试接口
@app.get("/test")
async def test():
    return create_response()

# OCR识别接口
@app.post("/ocr")
async def ocr_process(file: UploadFile = File(...)):
    try:
        # 验证文件类型
        allowed_types = {"image/jpeg", "image/png", "image/bmp"}
        if file.content_type not in allowed_types:
            return create_response(code=400, message="不支持的文件类型")
            
        # 验证文件大小（5MB）
        contents = await file.read()
        if len(contents) > 5 * 1024 * 1024:
            return create_response(code=400, message="文件大小超过限制")
            
        # 读取图片
        image = Image.open(io.BytesIO(contents))
        
        # 进行OCR识别
        result = ocr_processor.process_image(image)
        
        if not result:
            return create_response(code=400, message="未能识别到有效内容")
            
        return create_response(data=result)
        
    except Exception as e:
        return create_response(code=500, message=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 