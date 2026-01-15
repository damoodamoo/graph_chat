from pydantic import BaseModel, Field


class User(BaseModel):
    """Represents a customer/user from the graph database."""

    customer_id: str = Field(..., description="Unique customer identifier")
    age: int | None = Field(None, description="Customer's age")
    club_member_status: str | None = Field(
        None, description="Club membership status (e.g., ACTIVE, PRE-CREATE)"
    )
    fashion_news_frequency: str | None = Field(
        None, description="How often customer receives fashion news (e.g., NONE, Regularly)"
    )


class Article(BaseModel):
    """Represents a product/article from the graph database."""

    article_id: str = Field(..., description="Unique article identifier")
    product_code: str | None = Field(None, description="Product code")
    prod_name: str | None = Field(None, description="Product name")
    detail_desc: str | None = Field(None, description="Detailed product description")


class Preferences(BaseModel):
    prefs: list[Preference]


class Preference(BaseModel):
    item_type: str # colour_group or article
    value: str # value of colour or article_id
