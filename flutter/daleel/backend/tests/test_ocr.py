from io import BytesIO

from PIL import Image

from app.extensions import ocr
from app.integrations.contracts import ModuleNotConfigured, OcrRequest

png = BytesIO()
Image.new("RGB", (1, 1)).save(png, format="PNG")
PNG_BYTES = png.getvalue()


class FakeOcrEngine:
    def ocr(self, image, *, cls):
        assert image.shape == (1, 1, 3)
        assert cls is True
        return [[[None, ("سعر الوحدة", 0.96)], [None, ("٥ مليون", 0.91)]]]


def test_ocr_upload_extracts_text(client, monkeypatch):
    monkeypatch.setattr(ocr, "_ocr_engine", lambda: FakeOcrEngine())

    response = client.post(
        "/api/integrations/ocr/extract",
        data={"content_type": "image/png"},
        files={"file": ("brochure.png", PNG_BYTES, "application/octet-stream")},
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "integrated",
        "text": "سعر الوحدة\n٥ مليون",
        "fields": {},
        "confidence": 0.935,
    }
    ocr_module = next(module for module in client.get("/api/integrations").json()["modules"]
                      if module["module"] == "ocr")
    assert ocr_module["status"] == "integrated"


def test_ocr_upload_reports_unconfigured_model(client, app):
    def unconfigured(_):
        raise ModuleNotConfigured("Arabic model download is unavailable.")

    app.state.registry.register("ocr", unconfigured)
    response = client.post(
        "/api/integrations/ocr/extract",
        data={"content_type": "image/png"},
        files={"file": ("brochure.png", PNG_BYTES, "application/octet-stream")},
    )

    assert response.status_code == 503
    assert response.json()["status"] == "not_configured"


def test_ocr_upload_rejects_unsupported_file_type(client):
    response = client.post(
        "/api/integrations/ocr/extract",
        data={"content_type": "text/plain"},
        files={"file": ("brochure.txt", b"not an image", "text/plain")},
    )

    assert response.status_code == 415
    assert response.json()["error"]["message"] == "Upload a JPEG, PNG, or WebP image."


def test_ocr_upload_rejects_files_over_limit(client):
    response = client.post(
        "/api/integrations/ocr/extract",
        data={"content_type": "image/png"},
        files={"file": ("brochure.png", bytes(10 * 1024 * 1024 + 1), "application/octet-stream")},
    )

    assert response.status_code == 413
    assert response.json()["error"]["message"] == "The image exceeds the 10 MB limit."
