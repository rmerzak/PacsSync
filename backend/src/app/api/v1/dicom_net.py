import fastapi
from fastapi import UploadFile, File
from fastapi import Request, Response, status, Depends, HTTPException, File, UploadFile
from app.services.dicom_network_interface import DicomNetworkInterface
from app.core.container import Container
from dependency_injector.wiring import Provide
from app.core.middleware import inject
from app.services.dicom_meta_data_handler import DicomMetadataHandler
from io import BytesIO
import pydicom
from typing import Optional
router = fastapi.APIRouter(tags=["dicom_net"], prefix="/dicom_net")

@router.post("/upload_file")
@inject
async def upload_file(
    dicom_file: UploadFile = File(...),
    dicom_network_interface: DicomNetworkInterface = Depends(Provide[Container.dicom_network_interface])
):
    dicom_data = await dicom_file.read()
    dicom_io = BytesIO(dicom_data)
    try:
        dicom = pydicom.dcmread(dicom_io)
        dicomHandle = DicomMetadataHandler(dicom)
        extractor = dicomHandle.extract_full_metadata()
        processed_metadata = dicomHandle.extract_dicom_metadata(extractor)
        print("processed_metadata", processed_metadata)
        return await dicom_network_interface.upload_file_dataset(dicomHandle.dicom)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/find_studie")
@inject
async def find_studies(
    PatientID: Optional[str] = None,
    StudyInstanceUID: Optional[str] = None,
    AccessionNumber: Optional[str] = None,
    ModalitiesInStudy: Optional[str] = None,
    PatientName: Optional[str] = None,
    dicom_network_interface: DicomNetworkInterface = Depends(Provide[Container.dicom_network_interface])
):
    """
    Find all studies for a specific patient.
    This endpoint performs a DICOM C-FIND operation at the STUDY level.
    """
    query_params = {
        "PatientID": PatientID or "",
        "StudyInstanceUID": StudyInstanceUID or "",
        "StudyDate": "",
        "StudyTime": "",
        "StudyDescription": "",
        "AccessionNumber": AccessionNumber or "",
        "ModalitiesInStudy": ModalitiesInStudy or "",
        "NumberOfStudyRelatedSeries": "",
        "PatientName": PatientName or "",
        "PixelData": ""
    }
    
    return await dicom_network_interface.find_studies(query_params)

@router.get("/get_study")
@inject
async def get_study(
    StudyInstanceUID: str,
    dicom_network_interface: DicomNetworkInterface = Depends(Provide[Container.dicom_network_interface])
):
    """
    Retrieve a complete study including all DICOM instances.
    
    This endpoint performs a DICOM C-GET operation to retrieve all SOP Instances
    related to the specified study. The operation includes pixel data and all
    metadata for each instance.
    
    Args:
        StudyInstanceUID: The Study Instance UID to retrieve
        
    Returns:
        A DicomResult containing all retrieved instances with their metadata
    """
    return await dicom_network_interface.get_study_with_pixels(StudyInstanceUID)


@router.get("/get_instance")
@inject
async def get_instance(
    StudyInstanceUID: str,
    SeriesInstanceUID: str,
    SOPInstanceUID: str,
    dicom_network_interface: DicomNetworkInterface = Depends(Provide[Container.dicom_network_interface])
):
    """
    Retrieve a specific DICOM instance with its pixel data.
    
    This endpoint performs a DICOM C-GET operation at the INSTANCE level to retrieve
    a specific SOP Instance. The operation includes pixel data and all metadata.
    
    Args:
        StudyInstanceUID: The Study Instance UID
        SeriesInstanceUID: The Series Instance UID
        SOPInstanceUID: The SOP Instance UID
        
    Returns:
        A DicomResult containing the instance metadata and pixel data information
    """
    return await dicom_network_interface.get_instance_with_pixels(
        StudyInstanceUID, 
        SeriesInstanceUID, 
        SOPInstanceUID
    )
