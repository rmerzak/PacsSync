from app.services.base_service import BaseService
from app.services.dicom_network_interface import DicomNetworkInterface
from dataclasses import dataclass
from typing import  Optional, Dict, Any, List
from io import BytesIO
from pydicom import dcmread
from pydicom.dataset import Dataset
from pynetdicom import AE, evt, QueryRetrievePresentationContexts, StoragePresentationContexts, build_role
from pynetdicom.sop_class import (
    PatientRootQueryRetrieveInformationModelFind,
    PatientRootQueryRetrieveInformationModelGet,
    PatientRootQueryRetrieveInformationModelMove,
    StudyRootQueryRetrieveInformationModelFind,
    StudyRootQueryRetrieveInformationModelGet,
    StudyRootQueryRetrieveInformationModelMove
)
from pynetdicom.sop_class import UltrasoundImageStorage, CTImageStorage, MRImageStorage
from pynetdicom.status import code_to_category
from app.core.logger import logging
from app.core.config import ExternalSettings
from app.repository.user_repository import UserRepository
settings = ExternalSettings()
logger = logging.getLogger(__name__)

@dataclass
class DicomResult:
    success: bool
    message: str
    status_code: int
    data: Any = None

class DicomNetworkInterfaceImp(BaseService, DicomNetworkInterface):
    def __init__(self,user_repository: UserRepository, server_ip: str, server_port: int, server_ae_title: str, local_ae_title: str,timeout: int = 30):
        self.timeout = timeout
        self.server_ip = server_ip
        self.server_port = server_port
        self.server_ae_title = server_ae_title
        self.local_ae_title = local_ae_title
        self.user_repository = user_repository
    def get_transfer_syntaxes(self, dataset):
        """Get appropriate transfer syntaxes based on the dataset."""
        current_ts = getattr(dataset, 'file_meta', {}).get('TransferSyntaxUID', None)
        logger.info(f"Current transfer syntax: {current_ts}")

        basic_syntaxes = [
            "1.2.840.10008.1.2",       # Implicit VR Little Endian
            "1.2.840.10008.1.2.1",     # Explicit VR Little Endian
        ]

        jpeg_syntaxes = [
            "1.2.840.10008.1.2.4.50",  # JPEG Baseline
            "1.2.840.10008.1.2.4.51",  # JPEG Extended
            "1.2.840.10008.1.2.4.57",  # JPEG Lossless
        ]

        transfer_syntaxes = []
        if current_ts:
            transfer_syntaxes.append(current_ts)
        transfer_syntaxes.extend(jpeg_syntaxes)
        transfer_syntaxes.extend(basic_syntaxes)

        return list(dict.fromkeys(transfer_syntaxes))

    def setup_ae(self, contexts=None):
        """Set up Application Entity with appropriate contexts."""
        ae = AE(ae_title=self.local_ae_title)

        if contexts:
            for context in contexts:
                ae.add_requested_context(context)

        # Set timeouts
        ae.dimse_timeout = self.timeout
        ae.acse_timeout = self.timeout
        ae.network_timeout = self.timeout

        return ae

    def upload_file(self, dicom_data: bytes, filename: str) -> DicomResult:
        """Upload a single DICOM file using C-STORE."""
        try:
            dataset = dcmread(BytesIO(dicom_data))

            logger.info(f"Processing DICOM file: {filename}")
            logger.info(f"SOPClassUID: {getattr(dataset, 'SOPClassUID', 'Unknown')}")

            ae = self.setup_ae()
            transfer_syntaxes = self.get_transfer_syntaxes(dataset)
            ae.add_requested_context(dataset.SOPClassUID, transfer_syntaxes)
            print("**transfer_syntaxes***",transfer_syntaxes)
            print("**dataset.SOPClassUID**",dataset.SOPClassUID)

            def handle_store(event):
                return 0x0000

            assoc = ae.associate(
                self.server_ip,
                self.server_port,
                ae_title=self.server_ae_title,
                evt_handlers=[(evt.EVT_C_STORE, handle_store)]
            )

            if assoc.is_established:
                try:
                    status = assoc.send_c_store(dataset)
                    status_code = getattr(status, "Status", None)

                    if status and status_code == 0x0000:
                        assoc.release()
                        return DicomResult(
                            success=True,
                            message="DICOM file uploaded successfully",
                            status_code=200
                        )
                    else:
                        error_msg = f"Failed to store DICOM file. Status: {hex(status_code) if status_code else 'Unknown'}"
                        assoc.abort()
                        return DicomResult(success=False, message=error_msg, status_code=500)

                except Exception as e:
                    if assoc.is_established:
                        assoc.abort()
                    return DicomResult(success=False, message=f"Error during C-STORE: {str(e)}", status_code=500)
            else:
                return DicomResult(
                    success=False,
                    message="Failed to establish association",
                    status_code=500
                )

        except Exception as e:
            return DicomResult(
                success=False,
                message=f"Failed to process DICOM file: {str(e)}",
                status_code=400
            )

    async def upload_file_dataset(self, dataset: Dataset) -> DicomResult:
        """Upload a single DICOM file using C-STORE."""
        try:
            ae = self.setup_ae()
            transfer_syntaxes = self.get_transfer_syntaxes(dataset)
            ae.add_requested_context(dataset.SOPClassUID, transfer_syntaxes)

            def handle_store(event):
                return 0x0000

            assoc = ae.associate(
                self.server_ip,
                self.server_port,
                ae_title=self.server_ae_title,
                evt_handlers=[(evt.EVT_C_STORE, handle_store)]
            )

            if assoc.is_established:
                try:
                    status = assoc.send_c_store(dataset)
                    status_code = getattr(status, "Status", None)

                    if status and status_code == 0x0000:
                        assoc.release()
                        return DicomResult(
                            success=True,
                            message="DICOM file uploaded successfully",
                            status_code=200
                        )
                    else:
                        error_msg = f"Failed to store DICOM file. Status: {hex(status_code) if status_code else 'Unknown'}"
                        assoc.abort()
                        return DicomResult(success=False, message=error_msg, status_code=500)

                except Exception as e:
                    if assoc.is_established:
                        assoc.abort()
                    return DicomResult(success=False, message=f"Error during C-STORE: {str(e)}", status_code=500)
            else:
                return DicomResult(
                    success=False,
                    message="Failed to establish association",
                    status_code=500
                )

        except Exception as e:
            return DicomResult(
                success=False,
                message=f"Failed to process DICOM file: {str(e)}",
                status_code=400
            )

    async def find_studies(self, query_params: Dict) -> DicomResult:
        """Perform C-FIND operation for studies."""
        try:
            ae = AE(ae_title=self.local_ae_title)
            ae.add_requested_context(PatientRootQueryRetrieveInformationModelFind)
            
            ae.dimse_timeout = self.timeout
            ae.acse_timeout = self.timeout
            ae.network_timeout = self.timeout

            ds = Dataset()
            for key, value in query_params.items():
                setattr(ds, key, value)
            
            if 'PatientID' in query_params and not any(param in query_params for param in ['StudyInstanceUID', 'SeriesInstanceUID']):
                ds.QueryRetrieveLevel = 'PATIENT'
            elif 'StudyInstanceUID' in query_params and 'SeriesInstanceUID' not in query_params:
                ds.QueryRetrieveLevel = 'STUDY'
            elif 'SeriesInstanceUID' in query_params:
                ds.QueryRetrieveLevel = 'SERIES'
            else:
                ds.QueryRetrieveLevel = 'STUDY'

            results = []
            assoc = ae.associate(
                self.server_ip,
                self.server_port,
                ae_title=self.server_ae_title
            )

            if assoc.is_established:
                try:
                    responses = assoc.send_c_find(
                        ds,
                        PatientRootQueryRetrieveInformationModelFind
                    )
                    
                    for status, identifier in responses:
                        if status:
                            status_code = status.Status
                            logger.info(f"C-FIND query status: 0x{status_code:04X}")
                            
                            category = code_to_category(status_code)
                            
                            if status_code == 0xFF00:
                                if identifier:
                                    result_dict = {}
                                    for elem in identifier:
                                        if elem.keyword:
                                            if hasattr(elem, 'value'):
                                                if elem.VR == 'PN':
                                                    result_dict[elem.keyword] = str(elem.value)
                                                elif elem.VR == 'DA':
                                                    result_dict[elem.keyword] = str(elem.value)
                                                elif elem.VR == 'TM':
                                                    result_dict[elem.keyword] = str(elem.value)
                                                else:
                                                    result_dict[elem.keyword] = elem.value
                                    results.append(result_dict)
                            elif status_code == 0x0000:
                                logger.info("C-FIND completed successfully")
                            elif category in ['Cancel', 'Failure', 'Warning']:
                                logger.warning(f"C-FIND issue: {category} - Status: 0x{status_code:04X}")
                        else:
                            logger.error("Connection timed out, was aborted or received invalid response")
                    assoc.release()
                    return DicomResult(
                        success=True,
                        message="C-FIND completed successfully",
                        data=results,
                        status_code=200
                    )
                except Exception as e:
                    logger.error(f"Error during C-FIND: {str(e)}")
                    if assoc.is_established:
                        assoc.abort()
                    return DicomResult(
                        success=False,
                        message=f"Error during C-FIND: {str(e)}",
                        status_code=500
                    )
            else:
                logger.error("Failed to establish association for C-FIND")
                return DicomResult(
                    success=False,
                    message="Failed to establish association for C-FIND",
                    status_code=500
                )
        except Exception as e:
            logger.error(f"Exception in find_studies: {str(e)}")
            return DicomResult(
                success=False,
                message=f"Exception in find_studies: {str(e)}",
                status_code=500
            )

    def get_study(self, study_instance_uid: str) -> DicomResult:
        """Retrieve all DICOM data for a study using C-GET."""
        ae = AE()

        # Check the supported SOP classes
        ae.add_requested_context(PatientRootQueryRetrieveInformationModelGet)
        # ae.add_requested_context(UltrasoundImageStorage)
        supported_sop_classes = self._get_supported_sop_classes(ae)
        # if 'UltrasoundImageStorage' not in supported_sop_classes:
        #     return DicomResult(
        #         success=False,
        #         message="DICOM server does not support the UltrasoundImageStorage SOP class",
        #         status_code=400
        #     )

        # Add the requested presentation contexts
        ae.add_requested_context(PatientRootQueryRetrieveInformationModelGet)
        # ae.add_requested_context(UltrasoundImageStorage)
        ae.add_requested_context(CTImageStorage, ['1.2.840.10008.1.2.5', '1.2.840.10008.1.2.4.50', '1.2.840.10008.1.2.4.51', '1.2.840.10008.1.2.4.57', '1.2.840.10008.1.2', '1.2.840.10008.1.2.1'])

        ds = Dataset()
        ds.QueryRetrieveLevel = 'PATIENT'
        ds.PatientID = '2178309'
        # ds.StudyInstanceUID = ''
        # ds.SeriesInstanceUID = ''

        assoc = ae.associate(
            self.server_ip,
            self.server_port,
            ae_title=self.server_ae_title,
        )

        if assoc.is_established:
            try:
                responses = assoc.send_c_get(ds, PatientRootQueryRetrieveInformationModelGet)
                for (status, identifier) in responses:
                    if status:
                        print('C-GET query status: 0x{0:04x}'.format(status.Status))
                    else:
                        print('Connection timed out, was aborted or received invalid response')
            except Exception as e:
                return DicomResult(
                    success=False,
                    message=f"Error during C-GET: {str(e)}",
                    status_code=500
                )
            finally:
                assoc.release()
        else:
            return DicomResult(
                success=False,
                message="Failed to establish association for C-GET",
                status_code=500
            )

        return DicomResult(
            success=True,
            message="DICOM data retrieved successfully",
            status_code=200
        )

    def _get_supported_sop_classes(self, ae: AE) -> List[str]:
        """Retrieve the list of supported SOP classes from the DICOM server."""
        supported_sop_classes = []

        assoc = ae.associate(self.server_ip, self.server_port, ae_title=self.server_ae_title)
        if assoc.is_established:
            for context in assoc.accepted_contexts:
                supported_sop_classes.append(context.abstract_syntax)
            assoc.release()
        else:
            raise Exception("Failed to establish association to check supported SOP classes")

        return supported_sop_classes


    def move_study(self, study_instance_uid: str, destination_ae: str) -> DicomResult:
        """Move study to another AE using C-MOVE."""
        ae = self.setup_ae([StudyRootQueryRetrieveInformationModelMove])

        # Create C-MOVE dataset
        ds = Dataset()
        ds.StudyInstanceUID = study_instance_uid
        ds.QueryRetrieveLevel = 'STUDY'

        assoc = ae.associate(
            self.server_ip,
            self.server_port,
            ae_title=self.server_ae_title
        )

        if assoc.is_established:
            try:
                status = assoc.send_c_move(ds, destination_ae, StudyRootQueryRetrieveInformationModelMove)
                status = next(status)

                if status.Status == 0x0000:
                    assoc.release()
                    return DicomResult(
                        success=True,
                        message=f"C-MOVE to {destination_ae} completed successfully",
                        status_code=200
                    )
                else:
                    assoc.abort()
                    return DicomResult(
                        success=False,
                        message=f"C-MOVE failed with status: {hex(status.Status)}",
                        status_code=500
                    )
            except Exception as e:
                if assoc.is_established:
                    assoc.abort()
                return DicomResult(
                    success=False,
                    message=f"Error during C-MOVE: {str(e)}",
                    status_code=500
                )
        else:
            return DicomResult(
                success=False,
                message="Failed to establish association for C-MOVE",
                status_code=500
            )

    async def get_study_with_pixels(self, study_instance_uid: str) -> DicomResult:
        """
        Retrieve complete DICOM data for a study including pixel data using C-GET.
        
        This implementation follows the DICOM Query/Retrieve (Get) Service pattern
        where we request all SOP Instances related to a specific study.
        """
        try:
            # Set up the Application Entity
            ae = AE(ae_title=self.local_ae_title)
            
            # Add the requested presentation contexts for Query/Retrieve
            ae.add_requested_context(StudyRootQueryRetrieveInformationModelGet)
            
            # Add common storage contexts that might be needed for the retrieved images
            storage_contexts = [
                CTImageStorage,
                MRImageStorage,
                UltrasoundImageStorage,                
                # Add more storage classes as needed
            ]
            
            # Add each storage context and create role selection items
            roles = []
            for storage_class in storage_contexts:
                ae.add_requested_context(storage_class)
                # Create SCP/SCU Role Selection items (we'll act as SCP for storage)
                roles.append(build_role(storage_class, scp_role=True))
            
            # Set timeouts
            ae.dimse_timeout = self.timeout
            ae.acse_timeout = self.timeout
            ae.network_timeout = self.timeout
            
            # Create our query dataset
            ds = Dataset()
            ds.QueryRetrieveLevel = 'STUDY'
            ds.StudyInstanceUID = study_instance_uid
            
            # Store received datasets
            received_datasets = []
            
            # Implement handler for C-STORE operations triggered by C-GET
            def handle_store(event):
                """Handle a C-STORE request event."""
                dataset = event.dataset
                # Add file meta information
                if event.file_meta:
                    dataset.file_meta = event.file_meta
                
                # Store the dataset in memory
                received_datasets.append(dataset)
                
                logger.info(f"Received dataset: {dataset.SOPInstanceUID if hasattr(dataset, 'SOPInstanceUID') else 'Unknown'}")
                
                # Return success status
                return 0x0000
            
            # Associate with the peer AE
            assoc = ae.associate(
                self.server_ip,
                self.server_port,
                ae_title=self.server_ae_title,
                ext_neg=roles,
                evt_handlers=[(evt.EVT_C_STORE, handle_store)]
            )
            
            if assoc.is_established:
                try:
                    logger.info(f"Association established for C-GET of study {study_instance_uid}")
                    
                    # Send the C-GET request
                    responses = assoc.send_c_get(
                        ds, 
                        StudyRootQueryRetrieveInformationModelGet
                    )
                    
                    # Process the responses
                    completed = False
                    total_instances = 0
                    remaining = 0
                    failed = 0
                    warning = 0
                    
                    for status, identifier in responses:
                        if status:
                            status_code = status.Status
                            logger.info(f"C-GET status: 0x{status_code:04X}")
                            
                            # Check status category
                            category = code_to_category(status_code)
                            
                            if status_code == 0x0000:  # Success
                                completed = True
                                if hasattr(status, 'NumberOfCompletedSuboperations'):
                                    total_instances = status.NumberOfCompletedSuboperations
                                logger.info(f"C-GET completed successfully, received {total_instances} instances")
                                
                            elif category == 'Pending':
                                if hasattr(status, 'NumberOfRemainingSuboperations'):
                                    remaining = status.NumberOfRemainingSuboperations
                                if hasattr(status, 'NumberOfCompletedSuboperations'):
                                    total_instances = status.NumberOfCompletedSuboperations
                                if hasattr(status, 'NumberOfFailedSuboperations'):
                                    failed = status.NumberOfFailedSuboperations
                                if hasattr(status, 'NumberOfWarningSuboperations'):
                                    warning = status.NumberOfWarningSuboperations
                                    
                                logger.info(f"C-GET pending: completed={total_instances}, remaining={remaining}, failed={failed}, warning={warning}")
                                
                            elif category in ['Cancel', 'Failure', 'Warning']:
                                logger.warning(f"C-GET issue: {category} - Status: 0x{status_code:04X}")
                        else:
                            logger.error("Connection timed out, was aborted or received invalid response")
                    
                    # Process the received datasets
                    results = []
                    for dataset in received_datasets:
                        # Extract relevant information
                        result_dict = {}
                        
                        # Add basic identifiers
                        if hasattr(dataset, 'SOPInstanceUID'):
                            result_dict['SOPInstanceUID'] = str(dataset.SOPInstanceUID)
                        if hasattr(dataset, 'SeriesInstanceUID'):
                            result_dict['SeriesInstanceUID'] = str(dataset.SeriesInstanceUID)
                        if hasattr(dataset, 'StudyInstanceUID'):
                            result_dict['StudyInstanceUID'] = str(dataset.StudyInstanceUID)
                        
                        # Add metadata (excluding large binary data)
                        for elem in dataset:
                            if elem.keyword and elem.keyword != 'PixelData' and hasattr(elem, 'value'):
                                try:
                                    # Handle different VR types
                                    if elem.VR in ['PN', 'DA', 'TM', 'DT', 'LO', 'SH']:
                                        result_dict[elem.keyword] = str(elem.value)
                                    elif elem.VR in ['SQ']:  # Skip sequences for simplicity
                                        result_dict[elem.keyword] = "Sequence data available"
                                    elif elem.VR in ['OB', 'OW', 'OF', 'OD', 'UN']:
                                        # Skip binary data
                                        result_dict[elem.keyword] = f"{elem.VR} data ({len(elem.value)} bytes)"
                                    else:
                                        # Try to convert to a simple type
                                        if callable(elem.value):
                                            # Handle callable objects (this was causing the error)
                                            result_dict[elem.keyword] = f"Function: {elem.keyword}"
                                        elif hasattr(elem.value, '__dict__'):
                                            # Handle complex objects
                                            result_dict[elem.keyword] = f"Object: {elem.keyword}"
                                        else:
                                            # Try to convert to string
                                            result_dict[elem.keyword] = str(elem.value)
                                except Exception as e:
                                    # If conversion fails, just note that data exists
                                    result_dict[elem.keyword] = f"{elem.VR} data (conversion error)"
                                    logger.warning(f"Error converting {elem.keyword}: {str(e)}")
                        
                        # Check if pixel data exists
                        if hasattr(dataset, 'PixelData'):
                            result_dict['HasPixelData'] = True
                            result_dict['PixelDataLength'] = len(dataset.PixelData)
                            
                            # Add image dimensions if available
                            if hasattr(dataset, 'Rows') and hasattr(dataset, 'Columns'):
                                result_dict['ImageDimensions'] = f"{dataset.Rows}x{dataset.Columns}"
                            
                            # Add pixel spacing if available
                            if hasattr(dataset, 'PixelSpacing'):
                                try:
                                    result_dict['PixelSpacing'] = [float(x) for x in dataset.PixelSpacing]
                                except Exception as e:
                                    result_dict['PixelSpacing'] = f"Error converting: {str(e)}"
                        else:
                            result_dict['HasPixelData'] = False
                        
                        results.append(result_dict)
                    
                    # Release the association
                    assoc.release()
                    
                    # Create a summary of the results
                    summary = {
                        "total_instances": len(received_datasets),
                        "study_instance_uid": study_instance_uid,
                        "completed": completed,
                        "failed_operations": failed,
                        "warning_operations": warning
                    }
                    
                    return DicomResult(
                        success=True,
                        message=f"Retrieved {len(received_datasets)} DICOM instances for study {study_instance_uid}",
                        data={
                            "summary": summary,
                            "instances": results
                        },
                        status_code=200
                    )
                    
                except Exception as e:
                    logger.error(f"Error during C-GET: {str(e)}")
                    if assoc.is_established:
                        assoc.abort()
                    return DicomResult(
                        success=False,
                        message=f"Error during C-GET: {str(e)}",
                        status_code=500
                    )
            else:
                logger.error("Failed to establish association for C-GET")
                return DicomResult(
                    success=False,
                    message="Failed to establish association for C-GET",
                    status_code=500
                )
                
        except Exception as e:
            logger.error(f"Exception in get_study_with_pixels: {str(e)}")
            return DicomResult(
                success=False,
                message=f"Exception in get_study_with_pixels: {str(e)}",
                status_code=500
            )

    async def find_and_get_study(self, study_instance_uid: str) -> DicomResult:
        """
        First find study details using C-FIND, then retrieve the complete study using C-GET.
        This two-step approach allows determining the appropriate storage contexts before retrieval.
        """
        try:
            # Step 1: Perform C-FIND to get study details and determine modalities
            query_params = {
                "StudyInstanceUID": study_instance_uid,
                "ModalitiesInStudy": "",
                "StudyDescription": "",
                "PatientName": "",
                "PatientID": "",
                "StudyDate": "",
                "StudyTime": "",
                "AccessionNumber": "",
                "NumberOfStudyRelatedSeries": "",
                "NumberOfStudyRelatedInstances": ""
            }
            find_result = await self.find_studies(query_params)
            if not find_result.success or not find_result.data:
                return DicomResult(
                    success=False,
                    message=f"Study with UID {study_instance_uid} not found",
                    status_code=404
                )
            study_details = find_result.data[0] if isinstance(find_result.data, list) and find_result.data else {}
            modalities = []
            if 'ModalitiesInStudy' in study_details:
                if isinstance(study_details['ModalitiesInStudy'], str):
                    modalities = [m.strip() for m in study_details['ModalitiesInStudy'].split('\\')]
                elif isinstance(study_details['ModalitiesInStudy'], list):
                    modalities = study_details['ModalitiesInStudy']
            logger.info(f"Found study with modalities: {modalities}")
            ae = AE(ae_title=self.local_ae_title)
            ae.add_requested_context(StudyRootQueryRetrieveInformationModelGet)
            storage_contexts = []
            common_contexts = [
                CTImageStorage,
                MRImageStorage,
                UltrasoundImageStorage,
            ]
            for modality in modalities:
                if modality == 'CT':
                    storage_contexts.append(CTImageStorage)
                elif modality == 'MR':
                    storage_contexts.append(MRImageStorage)
                elif modality == 'US':
                    storage_contexts.append(UltrasoundImageStorage)
            if not storage_contexts:
                storage_contexts = common_contexts
            else:
                storage_contexts = list(set(storage_contexts + common_contexts))
            roles = []
            for storage_class in storage_contexts:
                ae.add_requested_context(storage_class)
                roles.append(build_role(storage_class, scp_role=True))
            ae.dimse_timeout = self.timeout
            ae.acse_timeout = self.timeout
            ae.network_timeout = self.timeout
            ds = Dataset()
            ds.QueryRetrieveLevel = 'STUDY'
            ds.StudyInstanceUID = study_instance_uid
            received_datasets = []
            def handle_store(event):
                """Handle a C-STORE request event."""
                dataset = event.dataset
                if event.file_meta:
                    dataset.file_meta = event.file_meta
                received_datasets.append(dataset)
                logger.info(f"Received dataset: {dataset.SOPInstanceUID if hasattr(dataset, 'SOPInstanceUID') else 'Unknown'}")
                return 0x0000
            assoc = ae.associate(
                self.server_ip,
                self.server_port,
                ae_title=self.server_ae_title,
                ext_neg=roles,
                evt_handlers=[(evt.EVT_C_STORE, handle_store)]
            )
            if assoc.is_established:
                try:
                    logger.info(f"Association established for C-GET of study {study_instance_uid}")
                    responses = assoc.send_c_get(
                        ds, 
                        StudyRootQueryRetrieveInformationModelGet
                    )
                    completed = False
                    total_instances = 0
                    remaining = 0
                    failed = 0
                    warning = 0
                    for status, identifier in responses:
                        if status:
                            status_code = status.Status
                            logger.info(f"C-GET status: 0x{status_code:04X}")
                            category = code_to_category(status_code)
                            if status_code == 0x0000:  # Success
                                completed = True
                                if hasattr(status, 'NumberOfCompletedSuboperations'):
                                    total_instances = status.NumberOfCompletedSuboperations
                                logger.info(f"C-GET completed successfully, received {total_instances} instances")
                            elif category == 'Pending':
                                if hasattr(status, 'NumberOfRemainingSuboperations'):
                                    remaining = status.NumberOfRemainingSuboperations
                                if hasattr(status, 'NumberOfCompletedSuboperations'):
                                    total_instances = status.NumberOfCompletedSuboperations
                                if hasattr(status, 'NumberOfFailedSuboperations'):
                                    failed = status.NumberOfFailedSuboperations
                                if hasattr(status, 'NumberOfWarningSuboperations'):
                                    warning = status.NumberOfWarningSuboperations
                                logger.info(f"C-GET pending: completed={total_instances}, remaining={remaining}, failed={failed}, warning={warning}")
                            elif category in ['Cancel', 'Failure', 'Warning']:
                                logger.warning(f"C-GET issue: {category} - Status: 0x{status_code:04X}")
                        else:
                            logger.error("Connection timed out, was aborted or received invalid response")
                    results = []
                    series_data = {}
                    for dataset in received_datasets:
                        result_dict = {}
                        if hasattr(dataset, 'SOPInstanceUID'):
                            result_dict['SOPInstanceUID'] = str(dataset.SOPInstanceUID)
                        if hasattr(dataset, 'SeriesInstanceUID'):
                            series_uid = str(dataset.SeriesInstanceUID)
                            result_dict['SeriesInstanceUID'] = series_uid
                            if series_uid not in series_data:
                                series_data[series_uid] = {
                                    'SeriesDescription': getattr(dataset, 'SeriesDescription', '') if hasattr(dataset, 'SeriesDescription') else '',
                                    'Modality': getattr(dataset, 'Modality', '') if hasattr(dataset, 'Modality') else '',
                                    'SeriesNumber': getattr(dataset, 'SeriesNumber', '') if hasattr(dataset, 'SeriesNumber') else '',
                                    'instances': []
                                }
                        if hasattr(dataset, 'StudyInstanceUID'):
                            result_dict['StudyInstanceUID'] = str(dataset.StudyInstanceUID)
                        for elem in dataset:
                            if elem.keyword and elem.keyword != 'PixelData' and hasattr(elem, 'value'):
                                try:
                                    if elem.VR in ['PN', 'DA', 'TM', 'DT', 'LO', 'SH']:
                                        result_dict[elem.keyword] = str(elem.value)
                                    elif elem.VR in ['SQ']:
                                        result_dict[elem.keyword] = "Sequence data available"
                                    elif elem.VR in ['OB', 'OW', 'OF', 'OD', 'UN']:
                                        result_dict[elem.keyword] = f"{elem.VR} data ({len(elem.value)} bytes)"
                                    else:
                                        if callable(elem.value):
                                            result_dict[elem.keyword] = f"Function: {elem.keyword}"
                                        elif hasattr(elem.value, '__dict__'):
                                            result_dict[elem.keyword] = f"Object: {elem.keyword}"
                                        else:
                                            result_dict[elem.keyword] = str(elem.value)
                                except Exception as e:
                                    result_dict[elem.keyword] = f"{elem.VR} data (conversion error)"
                                    logger.warning(f"Error converting {elem.keyword}: {str(e)}")
                        if hasattr(dataset, 'PixelData'):
                            result_dict['HasPixelData'] = True
                            result_dict['PixelDataLength'] = len(dataset.PixelData)
                            if hasattr(dataset, 'Rows') and hasattr(dataset, 'Columns'):
                                result_dict['ImageDimensions'] = f"{dataset.Rows}x{dataset.Columns}"
                            if hasattr(dataset, 'PixelSpacing'):
                                try:
                                    result_dict['PixelSpacing'] = [float(x) for x in dataset.PixelSpacing]
                                except Exception as e:
                                    result_dict['PixelSpacing'] = f"Error converting: {str(e)}"
                        else:
                            result_dict['HasPixelData'] = False
                        results.append(result_dict)
                        if hasattr(dataset, 'SeriesInstanceUID'):
                            series_uid = str(dataset.SeriesInstanceUID)
                            if series_uid in series_data:
                                series_data[series_uid]['instances'].append(result_dict)
                    assoc.release()
                    # Create a summary of the results
                    summary = {
                        "total_instances": len(received_datasets),
                        "total_series": len(series_data),
                        "study_instance_uid": study_instance_uid,
                        "study_details": study_details,
                        "completed": completed,
                        "failed_operations": failed,
                        "warning_operations": warning
                    }
                    series_list = [
                        {
                            "SeriesInstanceUID": series_uid,
                            "SeriesDescription": series_info['SeriesDescription'],
                            "Modality": series_info['Modality'],
                            "SeriesNumber": series_info['SeriesNumber'],
                            "InstanceCount": len(series_info['instances']),
                            "instances": series_info['instances']
                        }
                        for series_uid, series_info in series_data.items()
                    ]
                    series_list.sort(key=lambda x: int(x['SeriesNumber']) if x['SeriesNumber'] and str(x['SeriesNumber']).isdigit() else 9999)
                    return DicomResult(
                        success=True,
                        message=f"Retrieved {len(received_datasets)} DICOM instances for study {study_instance_uid}",
                        data={
                            "summary": summary,
                            "series": series_list
                        },
                        status_code=200
                    )
                except Exception as e:
                    logger.error(f"Error during C-GET: {str(e)}")
                    if assoc.is_established:
                        assoc.abort()
                    return DicomResult(
                        success=False,
                        message=f"Error during C-GET: {str(e)}",
                        status_code=500
                    )
            else:
                logger.error("Failed to establish association for C-GET")
                return DicomResult(
                    success=False,
                    message="Failed to establish association for C-GET",
                    status_code=500
                )
        except Exception as e:
            logger.error(f"Exception in find_and_get_study: {str(e)}")
            return DicomResult(
                success=False,
                message=f"Exception in find_and_get_study: {str(e)}",
                status_code=500
            )
