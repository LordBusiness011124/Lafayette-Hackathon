from pathlib import Path
import yaml
from app.schemas import Business
ROOT = Path(__file__).resolve().parents[1]
def load_business(path=None):
    return Business.model_validate(yaml.safe_load(Path(path or ROOT / "config/business.yaml").read_text()))
