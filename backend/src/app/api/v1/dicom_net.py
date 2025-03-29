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
    

@router.get("/find_studies")
@inject
async def find_studies(
    PatientName: Optional[str] = None,
    PatientID: Optional[str] = None,
    StudyDate: Optional[str] = None,
    StudyInstanceUID: Optional[str] = None,
    AccessionNumber: Optional[str] = None,  
    dicom_network_interface: DicomNetworkInterface = Depends(Provide[Container.dicom_network_interface])
):
    query_params = {}
    if PatientName:
        query_params["PatientName"] = PatientName
    if PatientID:
        query_params["PatientID"] = PatientID
    if StudyDate:
        query_params["StudyDate"] = StudyDate
    if StudyInstanceUID:
        query_params["StudyInstanceUID"] = StudyInstanceUID
    if AccessionNumber:
        query_params["AccessionNumber"] = AccessionNumber
    return await dicom_network_interface.find_studies(query_params)

@router.get("/find_patient")
@inject
async def find_patient(
    PatientID: str,
    dicom_network_interface: DicomNetworkInterface = Depends(Provide[Container.dicom_network_interface])
):
    """
    Find patient information using PatientID.
    This endpoint performs a DICOM C-FIND operation at the PATIENT level.
    """
    query_params = {
        "PatientID": PatientID,
        # Add any additional attributes you want to retrieve
        "PatientName": "",
        "PatientBirthDate": "",
        "PatientSex": ""
    }
    
    result = await dicom_network_interface.find_studies(query_params)
    return result

@router.get("/find_studies_by_patient")
@inject
async def find_studies_by_patient(
    PatientID: str,
    dicom_network_interface: DicomNetworkInterface = Depends(Provide[Container.dicom_network_interface])
):
    """
    Find all studies for a specific patient.
    This endpoint performs a DICOM C-FIND operation at the STUDY level.
    """
    query_params = {
        "PatientID": PatientID,
        "StudyInstanceUID": "",
        "StudyDate": "",
        "StudyTime": "",
        "StudyDescription": "",
        "AccessionNumber": "",
        "ModalitiesInStudy": "",
        "NumberOfStudyRelatedSeries": ""
    }
    
    result = await dicom_network_interface.find_studies(query_params)
    return result
