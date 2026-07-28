from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
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
    address_line_1 = Column(String)
    address_line_2 = Column(String)
    address_line_3 = Column(String)
    address_line_4 = Column(String)
    postal_code = Column(String)
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


class Fsp(Base):
    __tablename__ = "fsps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fsp_no = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    trading_name = Column(String)
    fsp_type = Column(String)
    registration_number = Column(String)
    date_authorised = Column(String)
    status = Column(String)
    physical_address = Column(Text)
    address_line_1 = Column(String)
    address_line_2 = Column(String)
    address_line_3 = Column(String)
    address_line_4 = Column(String)
    postal_code = Column(String)
    telephone = Column(String)
    scraped_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    compliance_officers = relationship(
        "FspComplianceOfficer",
        back_populates="fsp",
        cascade="all, delete-orphan",
    )
    representatives = relationship(
        "FspRepresentative",
        back_populates="fsp",
        cascade="all, delete-orphan",
    )
    key_individuals = relationship(
        "FspKeyIndividual",
        back_populates="fsp",
        cascade="all, delete-orphan",
    )
    approved_products = relationship(
        "FspApprovedProduct",
        back_populates="fsp",
        cascade="all, delete-orphan",
    )
    sole_proprietors = relationship(
        "FspSoleProprietor",
        back_populates="fsp",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Fsp(fsp_no={self.fsp_no!r}, name={self.name!r})>"


class FspComplianceOfficer(Base):
    __tablename__ = "fsp_compliance_officers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fsp_id = Column(Integer, ForeignKey("fsps.id"), nullable=False)
    name = Column(String, nullable=False)
    telephone = Column(String)

    fsp = relationship("Fsp", back_populates="compliance_officers")

    def __repr__(self) -> str:
        return f"<FspComplianceOfficer(name={self.name!r})>"


class FspRepresentative(Base):
    __tablename__ = "fsp_representatives"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fsp_id = Column(Integer, ForeignKey("fsps.id"), nullable=False)
    rep_id = Column(String)  # internal ID (e.g. maedegxelledt)
    full_names = Column(String, nullable=False)
    surname = Column(String, nullable=False)
    ki_of_rep = Column(String)

    fsp = relationship("Fsp", back_populates="representatives")
    products = relationship(
        "FspRepresentativeProduct",
        back_populates="representative",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<FspRepresentative(full_names={self.full_names!r}, surname={self.surname!r})>"


class FspKeyIndividual(Base):
    __tablename__ = "fsp_key_individuals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fsp_id = Column(Integer, ForeignKey("fsps.id"), nullable=False)
    ki_id = Column(String)  # internal ID (e.g. caeecgxlqqect)
    full_names = Column(String, nullable=False)
    surname = Column(String, nullable=False)
    class_of_business = Column(String)
    crypto_oversee = Column(String)

    fsp = relationship("Fsp", back_populates="key_individuals")
    cobs = relationship(
        "FspKeyIndividualClassOfBusiness",
        back_populates="key_individual",
        cascade="all, delete-orphan",
    )
    cryptos = relationship(
        "FspKeyIndividualCrypto",
        back_populates="key_individual",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<FspKeyIndividual(full_names={self.full_names!r}, surname={self.surname!r})>"


class FspRepresentativeProduct(Base):
    __tablename__ = "fsp_representative_products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    representative_id = Column(Integer, ForeignKey("fsp_representatives.id"), nullable=False)
    category = Column(String)
    subcategory = Column(String)
    product_name = Column(String, nullable=False)
    advice = Column(Boolean, default=False)
    intermediary_scripted = Column(Boolean, default=False)
    intermediary_other = Column(Boolean, default=False)
    under_supervision = Column(Boolean, default=False)
    category_code = Column(String)
    sub_category_code = Column(String)
    combined_code = Column(String)

    representative = relationship("FspRepresentative", back_populates="products")

    def __repr__(self) -> str:
        return f"<FspRepresentativeProduct(product_name={self.product_name!r})>"


class FspKeyIndividualClassOfBusiness(Base):
    __tablename__ = "fsp_key_individual_cobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key_individual_id = Column(Integer, ForeignKey("fsp_key_individuals.id"), nullable=False)
    cob_description = Column(String, nullable=False)
    category_i = Column(Boolean, default=False)
    category_ii = Column(Boolean, default=False)
    category_iia = Column(Boolean, default=False)
    category_iii = Column(Boolean, default=False)
    category_iv = Column(Boolean, default=False)
    category_code = Column(String)
    sub_category_code = Column(String)
    combined_code = Column(String)

    key_individual = relationship("FspKeyIndividual", back_populates="cobs")

    def __repr__(self) -> str:
        return f"<FspKeyIndividualClassOfBusiness(cob={self.cob_description!r})>"


class FspKeyIndividualCrypto(Base):
    __tablename__ = "fsp_key_individual_cryptos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key_individual_id = Column(Integer, ForeignKey("fsp_key_individuals.id"), nullable=False)
    category = Column(String)
    subcategory = Column(String)
    product_name = Column(String, nullable=False)
    advice = Column(Boolean, default=False)
    intermediary_scripted = Column(Boolean, default=False)
    intermediary_other = Column(Boolean, default=False)
    under_supervision = Column(Boolean, default=False)
    category_code = Column(String)
    sub_category_code = Column(String)
    combined_code = Column(String)

    key_individual = relationship("FspKeyIndividual", back_populates="cryptos")

    def __repr__(self) -> str:
        return f"<FspKeyIndividualCrypto(product_name={self.product_name!r})>"


class FspSoleProprietor(Base):
    __tablename__ = "fsp_sole_proprietors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fsp_id = Column(Integer, ForeignKey("fsps.id"), nullable=False)
    full_names = Column(String, nullable=False)
    surname = Column(String, nullable=False)
    conditions_apply = Column(String)

    fsp = relationship("Fsp", back_populates="sole_proprietors")
    products = relationship(
        "FspSoleProprietorProduct",
        back_populates="sole_proprietor",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<FspSoleProprietor(full_names={self.full_names!r}, surname={self.surname!r})>"


class FspSoleProprietorProduct(Base):
    __tablename__ = "fsp_sole_proprietor_products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sole_proprietor_id = Column(Integer, ForeignKey("fsp_sole_proprietors.id"), nullable=False)
    category = Column(String)
    subcategory = Column(String)
    product_name = Column(String, nullable=False)
    advice = Column(Boolean, default=False)
    intermediary_scripted = Column(Boolean, default=False)
    intermediary_other = Column(Boolean, default=False)
    under_supervision = Column(Boolean, default=False)
    category_code = Column(String)
    sub_category_code = Column(String)
    combined_code = Column(String)

    sole_proprietor = relationship("FspSoleProprietor", back_populates="products")

    def __repr__(self) -> str:
        return f"<FspSoleProprietorProduct(product_name={self.product_name!r})>"


class FspApprovedProduct(Base):
    __tablename__ = "fsp_approved_products"
    __table_args__ = (
        UniqueConstraint(
            "fsp_id", "category", "product_name", name="uq_fsp_product"
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    fsp_id = Column(Integer, ForeignKey("fsps.id"), nullable=False)
    category = Column(String, nullable=False)
    product_name = Column(String, nullable=False)
    advice_automated = Column(Boolean, default=False)
    advice_non_automated = Column(Boolean, default=False)
    intermediary_scripted = Column(Boolean, default=False)
    intermediary_other = Column(Boolean, default=False)
    category_code = Column(String)
    sub_category_code = Column(String)
    combined_code = Column(String)

    fsp = relationship("Fsp", back_populates="approved_products")

    def __repr__(self) -> str:
        return f"<FspApprovedProduct(category={self.category!r}, product_name={self.product_name!r})>"


def get_engine():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{DATABASE_PATH}", echo=False)


def create_tables(engine) -> None:
    Base.metadata.create_all(engine)


def get_session(engine):
    session_factory = sessionmaker(bind=engine)
    return session_factory()
