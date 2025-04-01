from abc import ABC, abstractmethod
from typing import List

class DicomPatientInterface(ABC):
    @abstractmethod
    def get_patient_by_id(self, patient_id: str):
        pass
    # @abstractmethod
    # def get_patient_by_name(self, patient_name: str):
    #     pass