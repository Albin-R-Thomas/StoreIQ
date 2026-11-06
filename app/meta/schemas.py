from pydantic import BaseModel, Field


class MetaMessage(BaseModel):
    id: str = Field(min_length=1, max_length=512)
    from_: str = Field(alias="from", min_length=1, max_length=50)
    type: str = Field(min_length=1, max_length=40)
    # Preserve text/audio/image and other provider fields without prematurely modelling them.
    model_config = {"extra": "allow"}


class MetaMetadata(BaseModel):
    phone_number_id: str = Field(min_length=1, max_length=100)


class MetaValue(BaseModel):
    metadata: MetaMetadata | None = None
    messages: list[MetaMessage] = Field(default_factory=list)


class MetaChange(BaseModel):
    field: str
    value: MetaValue


class MetaEntry(BaseModel):
    changes: list[MetaChange] = Field(default_factory=list)


class MetaWebhook(BaseModel):
    object: str
    entry: list[MetaEntry] = Field(default_factory=list)


class WebhookReceipt(BaseModel):
    accepted: int
    duplicates: int
