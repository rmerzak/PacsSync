from abc import ABC, abstractmethod
from typing import Dict, List, Any
from pydicom.dataset import Dataset
from dataclasses import dataclass

@dataclass
class DicomResult:
    success: bool
    message: str
    status_code: int
    data: Any = None

@dataclass
class DicomRequest:
    study_instance_uid: str
    series_instance_uid: str
    sop_instance_uid: str
    filename: str

class DicomNetworkInterface(ABC):
    # @abstractmethod
    # def send_dicom_request(self, dicom_request: DicomRequest):
    #     pass

    @abstractmethod
    def upload_file(self, dicom_data: bytes, filename: str) -> DicomResult:
        """Upload a single DICOM file using C-STORE."""
        pass
    
    @abstractmethod
    async def upload_file_dataset(self, dataset: Dataset) -> DicomResult:
        """Upload a single DICOM file using C-STORE."""
        pass
    
    @abstractmethod
    async def find_studies(self, query_params: Dict) -> Any:
        """
        Perform a C-FIND operation to query for studies.
        
        Args:
            query_params: Dictionary of DICOM attributes to query for
            
        Returns:
            Query results
        """
        pass
    
    @abstractmethod
    def get_study(self, study_instance_uid: str) -> DicomResult:
        """Retrieve all DICOM data for a study using C-GET."""
        pass
    
    @abstractmethod
    def move_study(self, study_instance_uid: str, destination_ae: str) -> DicomResult:
        """Move study to another AE using C-MOVE."""
        pass


