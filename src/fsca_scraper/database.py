from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker

from fsca_scraper.config import DATA_DIR, DATABASE_PATH


class Base(DeclarativeBase):
    pass


class ManagementCompany(Base):
    __tablename__ = "management_companies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    manager_no = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    company_type = Column(String)
    company_no = Column(String)
    local_foreign = Column(String)
    physical_address = Column(Text)
    telephone = Column(String)
    fax = Column(String)
    email = Column(String)
    website = Column(String)
    fsca_url = Column(String)
    scraped_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    schemes = relationship(
        "Scheme",
        back_populates="management_company",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<ManagementCompany(manager_no={self.manager_no!r}, name={self.name!r})>"


class Scheme(Base):
    __tablename__ = "schemes"
    __table_args__ = (
        UniqueConstraint(
            "scheme_no", "management_company_id", name="uq_scheme_per_company"
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    scheme_no = Column(String, nullable=False)
    name = Column(String, nullable=False)
    type_of_scheme = Column(String)
    representative_name = Column(String)
    status = Column(String)
    management_company_id = Column(
        Integer, ForeignKey("management_companies.id"), nullable=False
    )
    scraped_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    management_company = relationship("ManagementCompany", back_populates="schemes")
    portfolios = relationship(
        "Portfolio",
        back_populates="scheme",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Scheme(scheme_no={self.scheme_no!r}, name={self.name!r})>"


class Portfolio(Base):
    __tablename__ = "portfolios"
    __table_args__ = (
        UniqueConstraint("portfolio_no", "scheme_id", name="uq_portfolio_per_scheme"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_no = Column(String, nullable=False)
    name = Column(String, nullable=False)
    scheme_id = Column(Integer, ForeignKey("schemes.id"), nullable=False)
    scraped_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    scheme = relationship("Scheme", back_populates="portfolios")

    def __repr__(self) -> str:
        return f"<Portfolio(portfolio_no={self.portfolio_no!r}, name={self.name!r})>"


def get_engine():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{DATABASE_PATH}", echo=False)


def create_tables(engine) -> None:
    Base.metadata.create_all(engine)


def get_session(engine):
    session_factory = sessionmaker(bind=engine)
    return session_factory()
