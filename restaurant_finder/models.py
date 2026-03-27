"""レストランデータモデル."""

from dataclasses import dataclass, field


@dataclass
class ReviewSource:
    """各レビューサイトの評価情報."""
    source: str        # "tabelog", "hotpepper", "google"
    source_label: str   # "食べログ", "ホットペッパー", "Google"
    rating: float       # 0.0 - 5.0
    review_count: int
    url: str = ""


@dataclass
class Restaurant:
    """レストラン情報."""
    id: str
    name: str
    genre: str
    sub_genre: str = ""
    area: str = ""
    address: str = ""
    lat: float = 0.0
    lng: float = 0.0
    price_min: int = 0
    price_max: int = 0
    price_label: str = ""
    atmosphere_tags: list = field(default_factory=list)
    photos: list = field(default_factory=list)
    reviews: list = field(default_factory=list)
    overall_score: float = 0.0
    reservation_status: str = ""   # "available", "few", "full"
    reservation_label: str = ""
    open_hours: str = ""
    closed_days: str = ""
    capacity: int = 0
    has_private_room: bool = False
    smoking: str = ""
    description: str = ""
    features: list = field(default_factory=list)
    distance_meters: int = 0
    walk_minutes: int = 0
