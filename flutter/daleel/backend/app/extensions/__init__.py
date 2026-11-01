"""Register local model adapters here when they are ready."""


def register(registry):
    from .ocr import extract_image_text

    registry.register("ocr", extract_image_text)
