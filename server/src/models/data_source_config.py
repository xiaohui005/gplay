import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from src.db.database import Base


class DataSourceConfig(Base):
    __tablename__ = "data_source_config"

    source_id = Column(Integer, primary_key=True, autoincrement=True)
    source_code = Column(String(64), unique=True, nullable=False, comment="数据源标识 tushare_pro / akshare / baostock")
    source_name = Column(String(128), nullable=False, comment="数据源名称")
    base_url = Column(String(512), nullable=True, comment="API 基础地址")
    auth_info = Column(Text, nullable=True, comment="鉴权信息（JSON，加密存储）")
    rate_limit = Column(Integer, default=0, comment="每分钟请求限制，0 表示无限制")
    supported_data_types = Column(Text, nullable=True, comment="支持的数据类型列表 JSON 数组")
    enabled = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
