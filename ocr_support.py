"""Optional OCR utilities. OCR output is untrusted input and must be verified."""
from incremental_verification import extract_image_text

MAX_IMAGE_BYTES=8*1024*1024
ALLOWED_MIME={"image/png","image/jpeg","image/webp","image/tiff"}

def extract_upload(file_storage):
    if file_storage is None:
        raise ValueError("image file is required")
    mime=(file_storage.mimetype or "").lower()
    if mime not in ALLOWED_MIME:
        raise ValueError("Only PNG, JPEG, WEBP, and TIFF images are accepted.")
    data=file_storage.stream.read(MAX_IMAGE_BYTES+1)
    if not data:
        raise ValueError("Image file is empty.")
    if len(data)>MAX_IMAGE_BYTES:
        raise ValueError("Image exceeds the 8 MB limit.")
    result=extract_image_text(data)
    result["bytes_processed"]=len(data)
    result["warning"]="OCR can misread names, numbers, dates and negations. Check the original image before verification."
    return result
