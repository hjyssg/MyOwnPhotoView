from pydantic import BaseModel


class ScanFoldersPayload(BaseModel):
    folders: list[str]


class AppSettingsPayload(BaseModel):
    auto_scan_on_startup: bool
    scan_mode: str
