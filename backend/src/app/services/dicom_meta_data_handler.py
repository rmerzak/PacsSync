import pydicom
from typing import Dict, Any, Optional, Union
from io import BytesIO


class DicomMetadataHandler:
    def __init__(self, dicom_data):
        """Initialize the extractor with a DICOM file.

        Args:
            dicom_file: File-like object containing DICOM data
        """
        self.dicom = dicom_data
        self.metadata: Dict[str, Any] = {}

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
                    self.logger.warning(f"Tag {tag} not found and add_if_not_exists is False")
                    return False

                # Determine appropriate VR
                vr = self._determine_vr(tag, value)

                try:
                    # Add new tag with inferred VR
                    self.dicom.add_new(tag, vr, value)
                    return True
                except Exception as add_error:
                    self.logger.error(f"Could not add tag {tag}: {add_error}")
                    return False

        except Exception as e:
            self.logger.error(f"Error updating DICOM tag {tag}: {e}")
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

    # async def update_patient_dicom_tags(self, patient_data: dict) -> list:
    #     """Helper method to update or add patient-related DICOM tags
    #     explicitly.

    #     :param patient_data: Dictionary of patient information
    #     :return: List of successfully updated or added tags
    #     """
    #     tag_mappings = {
    #         '00100020': str(patient_data.get('id') or patient_data.get('patient_id')),
    #         '00100010': patient_data.get('patient_name') + ' ' + patient_data.get('patient_last_name') or patient_data.get('name'),
    #         '00100030': patient_data.get('birth_date').strftime('%Y%m%d') if patient_data.get('birth_date') else None,
    #         '00100040': patient_data.get('sex', 'F'),
    #         '00100050': patient_data.get('insurance_provider'),
    #     }

    #     successful_tags = []
    #     for tag, value in tag_mappings.items():
    #         if value is not None:  # Skip tags with None values
    #             try:
    #                 # Add the tag explicitly if missing
    #                 added = self.add_dicom_tag_if_missing(tag, value)
    #                 if not added:
    #                     # If not added, it exists, so update its value
    #                     self.update_dicom_tag(tag, value)
    #                 successful_tags.append(tag)
    #             except Exception as e:
    #                 print(f"Error updating or adding tag {tag}: {str(e)}")

    #     return successful_tags
    async def update_patient_dicom_tags(self, patient_data: dict) -> list:
        """Helper method to update or add patient-related DICOM tags
        explicitly. Continues processing even if individual tag updates fail.

        :param patient_data: Dictionary of patient information
        :return: List of successfully processed tags
        """
        tag_mappings = {
            '00100020': str(patient_data.get('id') or patient_data.get('patient_id')),
            '00100010': patient_data.get('patient_name', '') + ' ' + patient_data.get('patient_last_name', '') or patient_data.get('name', ''),
            '00100030': patient_data.get('birth_date').strftime('%Y%m%d') if patient_data.get('birth_date') else None,
            '00100040': patient_data.get('sex', 'F'),
            '00100050': patient_data.get('insurance_provider'),
        }

        processed_tags = []
        for tag, value in tag_mappings.items():
            if value is not None:
                try:
                    try:
                        self.add_dicom_tag_if_missing(tag, value)
                    except:
                        pass

                    try:
                        self.update_dicom_tag(tag, value)
                    except:
                        pass

                    processed_tags.append(tag)
                except Exception as e:
                    print(f"Non-critical error processing tag {tag}: {str(e)}")
                    processed_tags.append(tag)

        return processed_tags

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

    def _extract_file_meta(self) -> Dict[str, str]:
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
    def extract_frames_by_pixelData_length(self) -> Optional[int]:
        """Extract number of frames by checking the length of PixelData.

        Returns:
            Number of frames or None if retrieval fails
        """
        try:
            if 'NumberOfFrames' in self.dicom:
                return int(self.dicom.NumberOfFrames)

            if 'PixelData' in self.dicom:
                rows = int(self.dicom.get('Rows', 0))
                columns = int(self.dicom.get('Columns', 0))
                bits_allocated = int(self.dicom.get('BitsAllocated', 16))

                if rows > 0 and columns > 0 and bits_allocated > 0:
                    bytes_per_pixel = bits_allocated // 8

                    frame_size = rows * columns * bytes_per_pixel

                    total_pixel_data_length = len(self.dicom.PixelData)
                    num_frames = total_pixel_data_length // frame_size

                    return num_frames if num_frames > 0 else 1

            return 1
        except Exception:
            return None
    def extract_sr_referenced_instances(self) -> Optional[list[Dict[str, str]]]:
        """Extract Referenced SOP Instance UID and Series Instance UID for SR
        modality.

        Returns:
            List of dictionaries containing Referenced SOP Instance UID and Series Instance UID.
        """
        try:
            # Ensure the modality is SR
            modality = self._get_dicom_tag('00080060')  # Modality tag
            if modality != "SR":
                print("Modality is not SR, skipping extraction.")
                return None

            # Extract the sequence for tag 0040A375
            tag = '0040A375'
            if tag not in self.dicom:
                print("Tag 0040A375 not found in DICOM.")
                return None

            sequence_data = self.dicom[tag]
            referenced_data = []

            for item in sequence_data:
                series_sequence = item.get((0x0008, 0x1115))  # Referenced Series Sequence
                if series_sequence:
                    for series_item in series_sequence:
                        sop_sequence = series_item.get((0x0008, 0x1199))  # Referenced SOP Sequence
                        series_instance_uid = series_item.get((0x0020, 0x000E), '')  # Series Instance UID
                        if sop_sequence:
                            for sop_item in sop_sequence:
                                sop_instance_uid = sop_item.get((0x0008, 0x1155), '')  # Referenced SOP Instance UID

                                referenced_data.append({
                                    'SeriesInstanceUID': str(series_instance_uid.value),
                                    'ReferencedSOPInstanceUID': str(sop_instance_uid.value)
                                })

            return referenced_data if referenced_data else None

        except Exception as e:
            print(f"Error extracting SR referenced instances: {str(e)}")
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


    def extract_patient_id(self) -> Optional[int]:
        """Extract patient id information from DICOM tags.

        Returns:
            Integer representing patient id or None if not found
        """
        try:
            patient_id = self.dicom["00100020"].value
            return int(patient_id)
        except Exception:
            return None

    def extract_issuer_of_patient(self) -> Optional[int]:
        """Extract issuer of patient from DICOM tags.

        Returns:
            String representing issue ofpatient id or None if not found
        """
        try:
            issuer_of_patient_id = self.dicom["00100021"].value
            return int(issuer_of_patient_id)
        except Exception:
            return None

    def extract_full_metadata(self) -> Dict[str, Any]:
        """Extract comprehensive metadata using multiple methods.

        Returns:
            Comprehensive metadata dictionary
        """
        tag_metadata = self._extract_by_tags()
        attribute_metadata = self._extract_by_attributes()
        file_meta = self._extract_file_meta()
        pixel_info = self.extract_pixel_info_from_physical()
        frames = self.extract_frames_by_pixelData_length()
        ultrasound_region = self.extract_ultrasound_region()
        patient_id = self.extract_patient_id()
        issuer_of_patient_id = self.extract_issuer_of_patient()

        combined_metadata = {
            'tag_extraction': tag_metadata,
            'attribute_extraction': attribute_metadata,
            'file_metadata': file_meta,
            'pixel_info': pixel_info,
            'frames': frames,
            'ultrasound_region': ultrasound_region,
            'patient_id': patient_id,
            'issuer_of_patient_id': issuer_of_patient_id
        }

        return combined_metadata

    def extract_dicom_metadata(self, extractor):
        """Extract DICOM metadata with priority given to tag_extraction,
        falling back to attribute_extraction if needed.

        :param extractor: Dictionary containing extraction results
        :return: Dictionary with extracted metadata
        """
        def get_value(primary_path, fallback_path):
            """Try to get value from primary path, fallback to alternate path
            if not found.

            :param primary_path: Primary extraction path
                  (tag_extraction)
            :param fallback_path: Fallback extraction path
                  (attribute_extraction)
            :return: Extracted value or None
            """
            try:
                return primary_path
            except (KeyError, TypeError, IndexError):
                try:
                    return fallback_path
                except (KeyError, TypeError, IndexError):
                    return None

        frames = self.extract_frames_by_pixelData_length()
        modality = get_value(
            extractor['tag_extraction']['series_info']['Modality'],
            extractor['attribute_extraction']['series_info']['Modality']
        )
        if modality == 'SR':
            sr_refrenced_instances = self.extract_sr_referenced_instances()
        pixel_spacing = None
        if extractor.get('pixel_info'):
            try:
                pixel_spacing = [
                    extractor['pixel_info'].get('physical_delta_x', None),
                    extractor['pixel_info'].get('physical_delta_y', None)
                ]
            except Exception:
                pixel_spacing = None

        # Fallback pixel spacing extraction
        if not pixel_spacing:
            try:
                pixel_spacing = extractor['tag_extraction']['geometry']['PixelSpacing'].split('; ')
            except Exception:
                pixel_spacing = None
        metadata = {
            'study_instance_uid': get_value(
                extractor['tag_extraction']['study_info']['StudyInstanceUID'],
                extractor['attribute_extraction']['study_info']['StudyInstanceUID']
            ),
            'series_instance_uid': get_value(
                extractor['tag_extraction']['series_info']['SeriesInstanceUID'],
                extractor['attribute_extraction']['series_info']['SeriesInstanceUID']
            ),
            'instance_uid': get_value(
                extractor['tag_extraction']['image_info']['SOPInstanceUID'],
                extractor['attribute_extraction']['instance_info']['SOPInstanceUID']
            ),
            'description': get_value(
                extractor['tag_extraction']['study_info']['StudyDescription'],
                extractor['attribute_extraction']['series_info']['SeriesDescription']
            ),
            'frames': get_value(
                frames,
                extractor['attribute_extraction']['geometry']['NumberOfFrames']
            ),
            'modality': get_value(
                extractor['tag_extraction']['series_info']['Modality'],
                extractor['attribute_extraction']['series_info']['Modality']
            ),
            'pixel_spacing': pixel_spacing,
            'ultrasound_region': extractor.get('ultrasound_region'),
            "transfer_syntax": get_value(
                extractor['file_metadata']['TransferSyntaxUID'],
                extractor['tag_extraction']['transfer_syntax']['TransferSyntaxUID']
            ),
            "sop_class_uid": get_value(
                extractor['tag_extraction']['image_info']['SOPClassUID'],
                extractor['file_metadata']['MediaStorageSOPClassUID']
            ),
            "sr_referenced_instances": sr_refrenced_instances if modality == 'SR' else None,
            "issuer_of_patient_id": get_value(
                extractor['tag_extraction']['patient_info'].get('IssuerOfPatientID'),
                'DCM4CHEE'
            ),
            "patient_id": get_value(
                extractor['tag_extraction']['patient_info'].get('PatientID'),
                "1"
            ),
        }
        critical_fields = ['study_instance_uid', 'series_instance_uid', 'instance_uid', 'modality', 'transfer_syntax']
        missing_fields = [field for field in critical_fields if metadata[field] is None]

        if missing_fields:
            raise ValueError(f"Missing critical metadata fields: {', '.join(missing_fields)}")

        return metadata
    def update_dicom_tag(self, tag: str, value: Any) -> None:
        """Update a specific DICOM tag with a new value.

        Args:
            tag (str): DICOM tag to update
            value (Any): New value for the tag

        Raises:
            ValueError: If tag cannot be updated
        """
        try:
            self.dicom[tag].value = value
        except KeyError:
            raise ValueError(f"Tag {tag} not found in DICOM dataset")
        except Exception as e:
            raise ValueError(f"Unable to update tag {tag}: {str(e)}")

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


            #(0010,0010)	PN	Patient's Name
            #(0010,0020)	LO	Patient ID
            # dicomHandle.update_dicom_tag("00100020", str(existing_patient['id']))
            # dicomHandle.update_dicom_tag("00100010", str(existing_patient['patient_name']))
            # #(0010,0030)	DA	Patient's Birth Date
            # dicomHandle.update_dicom_tag("00100030", str(existing_patient['birth_date'].strftime('%Y%m%d')))
            # #(0010,0040)	CS	Patient's Sex
            # dicomHandle.update_dicom_tag("00100040", 'F')
            # #(0010,0050)	SQ	Patient's Insurance Plan Code Sequence
            # dicomHandle.update_dicom_tag("00100050", str(existing_patient['insurance_provider']))
            # #(0010,2154)	SH	Patient's Telephone Numbers
            # dicomHandle.update_dicom_tag("00102154", str(existing_patient['phone_number']))
            # #(0010,1040)	LO	Patient's Address
            # dicomHandle.update_dicom_tag("00101040", str(existing_patient['address']))


            #(0038,0300)	LO	Current Patient Location
            #(0038,0400)	LO	Patient's Institution Residence
            #(0038,0500)	LO	Patient State

            #(0008,0090)	PN	Referring Physician's Name
            #(0008,0092)	ST	Referring Physician's Address
            #(0008,0094)	SH	Referring Physician's Telephone Numbers


            #(0010,1000)	LO	Other Patient IDs
            #(0010,1001)	PN	Other Patient Names
            #(0010,1002)	SQ	Other Patient IDs Sequence
            #(0010,1060)	PN	Patient's Mother's Birth Name
            #(0010,2155)	LT	Patient's Telecom Information
            #(0018,9771)	SQ	Patient Physiological State Sequence
            #(0018,9772)	SQ	Patient Physiological State Code Sequence
            #(0010,21C0)	US	Pregnancy Status

            # (0008,1062)	SQ	Physician(s) Reading Study Identification Sequence
