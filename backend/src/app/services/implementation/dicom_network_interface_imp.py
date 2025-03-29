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
            # Create the appropriate AE with the right contexts
            ae = AE(ae_title=self.local_ae_title)
            ae.add_requested_context(PatientRootQueryRetrieveInformationModelFind)
            
            # Set timeouts
            ae.dimse_timeout = self.timeout
            ae.acse_timeout = self.timeout
            ae.network_timeout = self.timeout

            # Create the C-FIND dataset from the query parameters
            ds = Dataset()
            for key, value in query_params.items():
                setattr(ds, key, value)
            
            # Set the QueryRetrieveLevel based on the parameters
            if 'PatientID' in query_params and not any(param in query_params for param in ['StudyInstanceUID', 'SeriesInstanceUID']):
                ds.QueryRetrieveLevel = 'PATIENT'
            elif 'StudyInstanceUID' in query_params and 'SeriesInstanceUID' not in query_params:
                ds.QueryRetrieveLevel = 'STUDY'
            elif 'SeriesInstanceUID' in query_params:
                ds.QueryRetrieveLevel = 'SERIES'
            else:
                ds.QueryRetrieveLevel = 'STUDY'  # Default to STUDY level
            
            logger.info(f"C-FIND query parameters: {query_params}")
            logger.info(f"QueryRetrieveLevel: {ds.QueryRetrieveLevel}")

            results = []
            
            # Associate with the peer AE
            assoc = ae.associate(
                self.server_ip,
                self.server_port,
                ae_title=self.server_ae_title
            )

            if assoc.is_established:
                try:
                    # Send the C-FIND request
                    responses = assoc.send_c_find(
                        ds, 
                        PatientRootQueryRetrieveInformationModelFind
                    )
                    
                    for status, identifier in responses:
                        if status:
                            status_code = status.Status
                            logger.info(f"C-FIND query status: 0x{status_code:04X}")
                            
                            # Check the status category
                            category = code_to_category(status_code)
                            
                            if status_code == 0xFF00:  # Pending
                                if identifier:
                                    # Convert to dictionary for easier handling in API response
                                    result_dict = {}
                                    for elem in identifier:
                                        if elem.keyword:
                                            # Handle different VR types appropriately
                                            if hasattr(elem, 'value'):
                                                if elem.VR == 'PN':  # Person Name
                                                    result_dict[elem.keyword] = str(elem.value)
                                                elif elem.VR == 'DA':  # Date
                                                    result_dict[elem.keyword] = str(elem.value)
                                                elif elem.VR == 'TM':  # Time
                                                    result_dict[elem.keyword] = str(elem.value)
                                                else:
                                                    result_dict[elem.keyword] = elem.value
                                    
                                    results.append(result_dict)
                            
                            elif status_code == 0x0000:  # Success
                                logger.info("C-FIND completed successfully")
                            
                            elif category in ['Cancel', 'Failure', 'Warning']:
                                logger.warning(f"C-FIND issue: {category} - Status: 0x{status_code:04X}")
                        else:
                            logger.error("Connection timed out, was aborted or received invalid response")
                    
                    # Release the association
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
