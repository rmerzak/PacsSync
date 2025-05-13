import pydicom
from typing import Dict, Any, Optional, Union, List
from io import BytesIO
import logging

logger = logging.getLogger(__name__)

class DicomMetadataHandler:
    def __init__(self, dicom_data):
        """Initialize the extractor with a DICOM file.

        Args:
            dicom_file: File-like object containing DICOM data
        """
        self.dicom = dicom_data
        self.metadata: Dict[str, Any] = {}

    def extract_all_attributes(self) -> Dict[str, Any]:
        """
        Extract all attributes from the DICOM dataset.
        
        Returns:
            Dictionary containing all DICOM attributes with their values
        """
        result = {}
        
        # Process all elements in the dataset
        for elem in self.dicom:
            if elem.keyword:  # Skip elements without keywords
                try:
                    # Handle different VR types appropriately
                    if elem.VR in ['PN', 'DA', 'TM', 'DT', 'LO', 'SH', 'CS', 'UI', 'IS', 'DS', 'AS']:
                        # Convert these types to strings
                        result[elem.keyword] = str(elem.value) if elem.value is not None else None
                    elif elem.VR == 'SQ':
                        # For sequences, extract each item as a dictionary
                        if elem.value is not None:
                            seq_items = []
                            for item in elem.value:
                                item_dict = {}
                                for subelem in item:
                                    if subelem.keyword:
                                        try:
                                            if subelem.VR in ['PN', 'DA', 'TM', 'DT', 'LO', 'SH', 'CS', 'UI', 'IS', 'DS', 'AS']:
                                                item_dict[subelem.keyword] = str(subelem.value) if subelem.value is not None else None
                                            elif subelem.VR == 'SQ':
                                                item_dict[subelem.keyword] = "Nested sequence"
                                            elif subelem.VR in ['OB', 'OW', 'OF', 'OD', 'UN']:
                                                item_dict[subelem.keyword] = f"{subelem.VR} data ({len(subelem.value)} bytes)"
                                            else:
                                                item_dict[subelem.keyword] = subelem.value
                                        except Exception as e:
                                            item_dict[subelem.keyword] = f"Error: {str(e)}"
                                seq_items.append(item_dict)
                            result[elem.keyword] = seq_items
                        else:
                            result[elem.keyword] = None
                    elif elem.VR in ['OB', 'OW', 'OF', 'OD', 'UN']:
                        # For binary data, just note its presence and size
                        if elem.keyword == 'PixelData':
                            result[elem.keyword] = f"PixelData present ({len(elem.value)} bytes)"
                        else:
                            result[elem.keyword] = f"{elem.VR} data ({len(elem.value)} bytes)"
                    else:
                        # For other types, use the value directly
                        result[elem.keyword] = elem.value
                except Exception as e:
                    result[elem.keyword] = f"Error extracting value: {str(e)}"
        
        # Add file meta information if available
        if hasattr(self.dicom, 'file_meta'):
            file_meta = {}
            for elem in self.dicom.file_meta:
                if elem.keyword:
                    try:
                        if elem.VR in ['PN', 'DA', 'TM', 'DT', 'LO', 'SH', 'CS', 'UI', 'IS', 'DS', 'AS']:
                            file_meta[elem.keyword] = str(elem.value) if elem.value is not None else None
                        elif elem.VR in ['OB', 'OW', 'OF', 'OD', 'UN']:
                            file_meta[elem.keyword] = f"{elem.VR} data ({len(elem.value)} bytes)"
                        else:
                            file_meta[elem.keyword] = elem.value
                    except Exception as e:
                        file_meta[elem.keyword] = f"Error extracting value: {str(e)}"
            result['FileMetaInformation'] = file_meta
        
        # Add pixel data information
        if 'PixelData' in self.dicom:
            pixel_info = {}
            
            # Add image dimensions if available
            if hasattr(self.dicom, 'Rows') and hasattr(self.dicom, 'Columns'):
                pixel_info['Dimensions'] = f"{self.dicom.Rows}x{self.dicom.Columns}"
                pixel_info['Rows'] = int(self.dicom.Rows)
                pixel_info['Columns'] = int(self.dicom.Columns)
            
            # Add number of frames if available
            if hasattr(self.dicom, 'NumberOfFrames'):
                pixel_info['NumberOfFrames'] = int(self.dicom.NumberOfFrames)
            
            # Add pixel spacing if available
            if hasattr(self.dicom, 'PixelSpacing'):
                try:
                    pixel_info['PixelSpacing'] = [float(x) for x in self.dicom.PixelSpacing]
                except Exception as e:
                    pixel_info['PixelSpacing'] = f"Error converting: {str(e)}"
            
            # Add bits allocated/stored if available
            if hasattr(self.dicom, 'BitsAllocated'):
                pixel_info['BitsAllocated'] = int(self.dicom.BitsAllocated)
            if hasattr(self.dicom, 'BitsStored'):
                pixel_info['BitsStored'] = int(self.dicom.BitsStored)
            
            # Add photometric interpretation if available
            if hasattr(self.dicom, 'PhotometricInterpretation'):
                pixel_info['PhotometricInterpretation'] = str(self.dicom.PhotometricInterpretation)
            
            # Add samples per pixel if available
            if hasattr(self.dicom, 'SamplesPerPixel'):
                pixel_info['SamplesPerPixel'] = int(self.dicom.SamplesPerPixel)
            
            result['PixelDataInfo'] = pixel_info
        
        return result

    @staticmethod
    def _determine_vr(tag: Union[str, pydicom.tag.Tag], value: Any) -> str:
        """Determine the appropriate Value Representation (VR) for a given tag.

        :param tag: DICOM tag
        :param value: Value to be set
        :return: Appropriate VR for the tag
        """
        # Define VR mappings for common tag types
        vr_mappings = {
            # Patient Information Tags
            '00100010': 'PN',  # Patient Name
            '00100020': 'LO',  # Patient ID
            '00100030': 'DA',  # Patient Birth Date
            '00100040': 'CS',  # Patient Sex
            # '00100050': 'LO',  # Patient Insurance Plan Code
            '00100021': 'LO',  # Issuer of Patient ID

            # Contact and Demographic Tags
            '00101040': 'LO',  # Patient Address
            '00102154': 'SH',  # Patient Telephone Numbers
            '00100050': 'SQ',  # Patient's Insurance Plan Code

            # Study Information Tags
            '0020000D': 'UI',  # Study Instance UID
            '00080020': 'DA',  # Study Date
            '00080030': 'TM',  # Study Time

            # Institution Tags
            '00080080': 'LO',  # Institution Name
            '00081040': 'LO',  # Institutional Department Name
        }

        # Convert tag to string if it's a pydicom Tag
        tag_str = str(tag) if isinstance(tag, pydicom.tag.Tag) else tag

        # Lookup specific VR, fallback to type inference
        vr = vr_mappings.get(tag_str)

        if vr:
            return vr

        # Type inference if no specific mapping
        if isinstance(value, str):
            return 'LO'  # Long String
        elif isinstance(value, int):
            return 'IS'  # Integer String
        elif isinstance(value, float):
            return 'DS'  # Decimal String
        elif isinstance(value, list):
            return 'SQ'  # Sequence
        else:
            return 'UN'  # Unknown

    def update_dicom_tag(
        self,
        tag: Union[str, tuple, pydicom.tag.Tag],
        value: Any,
        add_if_not_exists: bool = True
    ) -> bool:
        """Update or add a DICOM tag with flexible handling.

        :param tag: DICOM tag (hex string, tuple, or pydicom Tag)
        :param value: Value to set for the tag
        :param add_if_not_exists: Whether to add tag if not found
        :return: Boolean indicating successful update/addition
        """
        try:
            # Normalize tag representation
            if isinstance(tag, str):
                # Convert hex string to tuple if needed
                tag = (int(tag[:4], 16), int(tag[4:], 16))

            # Attempt to update existing tag
            try:
                self.dicom[tag].value = value
                return True
            except KeyError:
                # Tag not found
                if not add_if_not_exists:
                    logger.warning(f"Tag {tag} not found and add_if_not_exists is False")
                    return False

                # Determine appropriate VR
                vr = self._determine_vr(tag, value)

                try:
                    # Add new tag with inferred VR
                    self.dicom.add_new(tag, vr, value)
                    return True
                except Exception as add_error:
                    logger.error(f"Could not add tag {tag}: {add_error}")
                    return False

        except Exception as e:
            logger.error(f"Error updating DICOM tag {tag}: {e}")
            return False

    def bulk_update_tags(
        self,
        tag_updates: dict
    ) -> list:
        """Perform bulk updates to multiple DICOM tags.

        :param tag_updates: Dictionary of tags to update {tag: value}
        :return: List of successfully updated tags
        """
        successful_tags = []
        for tag, value in tag_updates.items():
            if self.update_dicom_tag(tag, value):
                successful_tags.append(tag)
        return successful_tags

    def add_dicom_tag_if_missing(
    self,
    tag: Union[str, tuple, pydicom.tag.Tag],
    value: Any
    ) -> bool:
        """Explicitly add a DICOM tag if it does not exist.

        :param tag: DICOM tag (hex string, tuple, or pydicom Tag)
        :param value: Value to set for the tag
        :return: Boolean indicating whether the tag was added
        """
        try:
            # Normalize tag representation
            if isinstance(tag, str):
                tag = (int(tag[:4], 16), int(tag[4:], 16))  # Convert hex string to tuple

            # Check if tag exists
            if tag not in self.dicom:
                # Determine appropriate VR
                vr = self._determine_vr(tag, value)

                # Add the tag with the inferred VR and value
                self.dicom.add_new(tag, vr, value)
                return True
            return False  # Tag already exists, no action taken
        except Exception as e:
            raise ValueError(f"Error adding DICOM tag {tag}: {str(e)}")

    def extract_full_metadata(self) -> Dict[str, Any]:
        """
        Extract comprehensive metadata from the DICOM file.
        
        Returns:
            Dictionary containing all extracted metadata
        """
        metadata = {
            'all_attributes': self.extract_all_attributes(),
            'tag_extraction': self._extract_by_tags(),
            'attribute_extraction': self._extract_by_attributes(),
            'file_metadata': self._extract_file_metadata(),
            'pixel_info': self.extract_pixel_info_from_physical(),
            'ultrasound_region': self.extract_ultrasound_region() if hasattr(self.dicom, 'Modality') and self.dicom.Modality == 'US' else None
        }
        
        return metadata

    def _extract_by_tags(self) -> Dict[str, Dict[str, str]]:
        """Extract metadata using DICOM tags.

        Returns:
            Dictionary of metadata extracted by tags
        """
        tag_mappings = {
            'patient_info': {
                'PatientName': '00100010',
                'PatientID': '00100020',
                'PatientBirthDate': '00100030',
                'PatientSex': '00100040',
                'PatientAge': '00101010',
                'PatientWeight': '00101030',
                'IssuerOfPatientID': '00100021'
            },
            'study_info': {
                'StudyInstanceUID': '0020000D',
                'StudyDate': '00080020',
                'StudyTime': '00080030',
                'StudyDescription': '00081030',
                'StudyID': '00200010',
                'AccessionNumber': '00080050',
                'ReferringPhysicianName': '00080090',
                'PerformingPhysicianName': '00081050',
                'InstitutionName': '00080080',
                'InstitutionAddress': '00080081'
            },
            'series_info': {
                'SeriesInstanceUID': '0020000E',
                'SeriesNumber': '00200011',
                'Modality': '00080060',
                'SeriesDescription': '0008103E',
                'AcquisitionDate': '00080022',
                'AcquisitionTime': '00080032',
                'AcquisitionNumber': '00200012',
                'AcquisitionProtocolName': '00181030'
            },
            'image_info': {
                'SOPInstanceUID': '00080018',
                'SOPClassUID': '00080016',
                'ImageType': '00080008',
                'InstanceCreationDate': '00080012',
                'InstanceCreationTime': '00080013'
            },
            'transfer_syntax': {
                'TransferSyntaxUID': '00020010',
                'ReferencedTransferSyntaxUI': '00041512',
                'MACCalculationTransferSyntaxUID': '04000010',
                'EncryptedContentTransferSyntaxUID': '04000500'
            },
            'geometry': {
                'PixelSpacing': '00280030',
                'Height': '00280010',
                'Width': '00280011',
                'NumberOfFrames': '00280008',
                'SliceThickness': '00180050',
                'PhotometricInterpretation': '00280004',
                'PhysicalDeltaX': '0018602c',
                'PhysicalDeltaY': '0018602e'
            },
            'device_info': {
                'Manufacturer': '00080070',
                'ManufacturerModelName': '00080080',
                'DeviceSerialNumber': '00181000'
            },
            'protocol_info': {
                'ProtocolName': '00181030',
                'ContrastBolusAgent': '00180010'
            },
            'pixel_data': {
                'BitsAllocated': '00280100',
                'BitsStored': '00280101',
                'HighBit': '00280102',
                'PixelRepresentation': '00280103'
            }
        }

        tag_metadata = {
            category: {
                key: self._get_dicom_tag(tag)
                for key, tag in category_tags.items()
            }
            for category, category_tags in tag_mappings.items()
        }

        return tag_metadata

    def _extract_by_attributes(self) -> Dict[str, Any]:
        """Extract metadata using DICOM object attributes.

        Returns:
            Dictionary of metadata extracted by attributes
        """
        attribute_mappings = {
            'patient_info': [
                'PatientName', 'PatientID', 'PatientBirthDate',
                'PatientSex', 'PatientAge', 'PatientWeight'
            ],
            'study_info': [
                'StudyInstanceUID', 'StudyDate', 'StudyTime',
                'StudyDescription', 'StudyID'
            ],
            'series_info': [
                'SeriesInstanceUID', 'SeriesNumber',
                'Modality', 'SeriesDescription'
            ],
            'instance_info': [
                'SOPInstanceUID', 'SOPClassUID', 'ImageType',
                'InstanceCreationDate', 'InstanceCreationTime'
            ],
            'geometry': [
                'PixelSpacing', 'Height', 'Width', 'NumberOfFrames',
                'SliceThickness', 'PhotometricInterpretation',
                'PhysicalDeltaX', 'PhysicalDeltaY'
            ],
            'device_info': [
                'Manufacturer', 'ManufacturerModelName', 'DeviceSerialNumber'
            ],
            'pixel_data': [
                'BitsAllocated', 'BitsStored', 'HighBit', 'PixelRepresentation'
            ]
        }

        extracted = {}
        for category, attributes in attribute_mappings.items():
            extracted[category] = {}
            for attr in attributes:
                try:
                    value = getattr(self.dicom, attr, '')
                    extracted[category][attr] = str(value) if value else ''
                except Exception:
                    extracted[category][attr] = ''

        return extracted

    def _extract_file_metadata(self) -> Dict[str, str]:
        """Extract file metadata from dicom.file_meta.

        Returns:
            Dictionary of file metadata
        """
        file_meta_attributes = [
            'MediaStorageSOPClassUID',
            'MediaStorageSOPInstanceUID',
            'TransferSyntaxUID',
            'ImplementationClassUID'
        ]

        extracted = {}
        for attr in file_meta_attributes:
            try:
                value = getattr(self.dicom.file_meta, attr, '')
                extracted[attr] = str(value) if value else ''
            except Exception:
                extracted[attr] = ''

        return extracted

    def extract_pixel_info_from_physical(self) -> Optional[Dict[str, float]]:
        """Extract pixel information from physical tags.

        Returns:
            Dictionary of pixel information or None if retrieval fails
        """
        try:
            physical_delta_x = round(float(self.dicom["00186011"][0]["0018602C"].value) * 10, 5)
            physical_delta_y = round(float(self.dicom["00186011"][0]["0018602E"].value) * 10, 5)

            return {
                'physical_delta_x': physical_delta_x,
                'physical_delta_y': physical_delta_y
            }
        except Exception:
            return None

    def extract_pixel_info_by_frame_index(self, frame_index: int) -> Optional[Dict[str, Any]]:
        """Extract pixel information for a specific frame.

        Args:
            frame_index (int): Index of the frame to extract

        Returns:
            Dictionary of pixel information or None if retrieval fails
        """
        try:
            # this function will be used in claruis dicoms getting the pixel data for each frame
            physical_delta_x = round(float(self.dicom["00186011"][frame_index]["0018602C"].value) * 10, 5)
            physical_delta_y = round(float(self.dicom["00186011"][frame_index]["0018602E"].value) * 10, 5)
            pixel_info = {
                'frame_index': frame_index,
                'physical_delta_x': physical_delta_x,
                'physical_delta_y': physical_delta_y,
            }
            return pixel_info
        except Exception:
            return None

    def extract_ultrasound_region(self) -> Optional[int]:
        """Extract ultrasound region information from DICOM tags.

        Returns:
            Integer representing ultrasound region or None if not found
        """
        try:
            ultrasound_region = self.dicom["00186011"][0]['0018601A'].value
            return int(ultrasound_region)
        except Exception:
            return None

    def extract_dicom_metadata(self, extractor: Dict[str, Any]):
        """
        Extract and process DICOM metadata from the extractor results.
        
        Args:
            extractor: Dictionary containing extracted metadata
            
        Returns:
            DicomResult containing processed metadata
        """
        # Use the all_attributes data for a comprehensive result
        all_attributes = extractor.get('all_attributes', {})
        
        # Create a DicomResult with the comprehensive data
        return all_attributes


    def _get_dicom_tag(self, tag: str, default=""):
        """Extract value for a specific DICOM tag.

        Args:
            tag (str): DICOM tag to extract, can be in formats like '6513213' or ['312312']['65321']
            default (str, optional): Default value if tag not found

        Returns:
            str: Extracted tag value
        """

        try:
            # Handle nested tag formats like ['312312']['65321']
            if isinstance(tag, list):
                current_value = self.dicom
                for t in tag:
                    current_value = current_value[t]
                value = current_value.value
            else:
                # Regular single tag handling
                value = self.dicom[tag].value

            # Handle different value types
            if isinstance(value, (list, pydicom.multival.MultiValue)):
                return '; '.join(str(v) for v in value)
            elif isinstance(value, bytes):
                return value.decode('utf-8', errors='ignore')
            return str(value)
        except Exception:
            return default