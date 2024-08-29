import sqlalchemy
import logging
import uuid

from enum import Enum as ENUM

from sqlalchemy import Column, String, Enum, LargeBinary, DateTime
from sqlalchemy.orm import Session, DeclarativeBase
from sqlalchemy.dialects.postgresql import UUID


class STATUS_CODE(ENUM):
    FAILED = 0
    FAILED_TRY_AGAIN = 1
    RECEIVED = 2
    PROCESSING = 3
    SUCCESS = 4


class FileObject:
    def __init__(self, file_data, file_name, mimetype):
        self.stream = file_data
        self.filename = file_name
        self.mimetype = mimetype

    def __repr__(self):
        return f"FileObject(filename={self.filename}, mimetype={self.mimetype})"


class DatabaseClient:
    def __init__(self, db_type, database, username, password, host, port=None):
        if db_type.lower() == 'mssql':
            driver = 'mssql+pymssql'
        elif db_type.lower() == 'mariadb':
            driver = 'mariadb+mariadbconnector'
        elif db_type.lower() == 'postgresql':
            driver = 'postgresql+psycopg2'
        else:
            raise ValueError(f"Invalid database type {type}")

        self.logger = logging.getLogger(__name__)

        if port:
            host = host + f':{port}'

        self.engine = sqlalchemy.create_engine(f'{driver}://{username}:{password}@{host}/{database}')

    def get_engine(self):
        return self.engine
    
    def get_connection(self):
        try:
            if self.engine:
                return self.engine.connect()
            self.logger.error("DatabaseClient not initialized properly. Engine is None. Check error from init.")
        except Exception as e:
            self.logger.error(f"Error connecting to database: {e}")

    def get_session(self):
        try:
            if self.engine:
                return Session(self.get_engine())
            self.logger.error("DatabaseClient not initialized properly. Engine is None. Check error from init.")
        except Exception as e:
            self.logger.error(f"Error connecting to database: {e}")

    def execute_sql(self, sql):
        try:
            with self.get_connection() as conn:
                res = conn.execute(sqlalchemy.text(sql))
                conn.commit()
                return res
        except Exception as e:
            self.logger.error(f"Error executing SQL: {e}")

    def add_object(self, session, obj):
        try:
            session.add(obj)
            session.commit()
            return True
        except Exception as e:
            self.logger.error(f"Error adding object to database: {e}")

    def get_signatur_file_upload(self, session, id):
        try:
            upload = session.query(SignaturFileupload).filter(SignaturFileupload.id == id).first()
            return upload
        except Exception as e:
            self.logger.error(f"Error getting object from database: {e}")

    def get_all_signatur_file_uploads(self, session):
        try:
            uploads = session.query(SignaturFileupload).all()
            return uploads
        except Exception as e:
            self.logger.error(f"Error getting object from database: {e}")

    def get_next_signatur_file_upload(self, session):
        try:
            upload = session.query(SignaturFileupload).filter(SignaturFileupload.status == STATUS_CODE.RECEIVED).order_by(SignaturFileupload.updated_at.asc()).with_for_update().first()
            if upload:
                upload.status = STATUS_CODE.PROCESSING
            session.commit()
            return upload
        except Exception as e:
            self.logger.error(f"Error getting object from database: {e}")


class Base(DeclarativeBase):
    pass


class SignaturFileupload(Base):
    __tablename__ = 'signatur_fileupload'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cpr = Column(String, nullable=False)
    institutionIdentifier = Column(String, nullable=False)
    employment = Column(String, nullable=False)
    message = Column(String, nullable=True)
    status = Column(Enum(STATUS_CODE), nullable=False, default=STATUS_CODE.RECEIVED)
    file_data = Column(LargeBinary, nullable=False)
    file_name = Column(String, nullable=False)
    file_mimetype = Column(String, nullable=False)
    updated_at = Column(DateTime, onupdate=sqlalchemy.func.now())

    @property
    def file(self):
        return FileObject(self.file_data, self.file_name, self.file_mimetype)

    def __init__(self, file, institutionIdentifier: str, employment: str, cpr: str):
        self.file_data = file.read()
        self.file_name = file.filename
        self.file_mimetype = file.mimetype
        self.institutionIdentifier = institutionIdentifier
        self.employment = employment
        self.cpr = cpr
        self.set_status(STATUS_CODE.RECEIVED, 'File upload received')

    def __repr__(self):
        return f"<file:{self.file_name} employment:{self.employment} cpr:{self.cpr} id:{self.id}>"

    def get_id(self):
        return self.id
    
    def update_values(self, file, institutionIdentifier, employment, cpr):
        self.file_data = file.read()
        self.file_name = file.filename
        self.file_mimetype = file.mimetype
        self.institutionIdentifier = institutionIdentifier
        self.employment = employment
        self.cpr = cpr
        self.set_status(STATUS_CODE.RECEIVED, 'File upload updated')
    
    def set_status(self, status, message):
        self.status = status
        self.message = message
    
    def get_status(self):
        return self.status, self.message