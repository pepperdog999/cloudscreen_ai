from fastapi import FastAPI, UploadFile, File, HTTPException, Header, Depends
from fastapi.responses import JSONResponse
from PIL import Image
import io
from ocr import OCRProcessor
from typing import Optional

app = FastAPI(title="OCR API Service")

# 初始化OCR处理器
ocr_processor = OCRProcessor()

# API Token
VALID_TOKEN = "QcZcTFNtHjXqgUgKedBVSENQsoRruorlYmXRynMFofH"

# 验证函数
async def verify_token(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="未提供认证信息"
        )
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != 'bearer':
            raise HTTPException(
                status_code=401,
                detail="认证格式错误"
            )
        if token != VALID_TOKEN:
            raise HTTPException(
                status_code=401,
                detail="无效的Token"
            )
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="认证格式错误"
        )
    
    return token

# 基础响应模型
def create_response(code: int = 200, message: str = "success", data: any = None):
    return {
        "code": code,
        "message": message,
        "data": data
    }

# 测试接口
@app.get("/test")
async def test(token: str = Depends(verify_token)):
    return create_response()

# OCR识别接口
@app.post("/ocr")
async def ocr_process(
    file: UploadFile = File(...),
    token: str = Depends(verify_token)
):
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
    print("正在启动服务...")
    import uvicorn
    uvicorn.run(
        "main:app",  # 修改这里，使用字符串形式指定应用
        host="0.0.0.0",
        port=8000,
        workers=4,
        reload=True  # 添加热重载功能
    ) 