import logging
import os
from pydicom import dcmread
from pynetdicom import AE, evt, debug_logger, StoragePresentationContexts
from pynetdicom.sop_class import Verification, CTImageStorage
debug_logger()
dicom_file_path = "./dicom_test/102.dcm"

if os.path.exists(dicom_file_path):
    dataset = dcmread(dicom_file_path)
    
    # Check if the DICOM file is compressed and decompress if needed
    transfer_syntax = dataset.file_meta.TransferSyntaxUID
    ae = AE()
    ae.requested_contexts = StoragePresentationContexts[:127]
    association = ae.associate('127.0.0.1', 11112, ae_title="DCM4CHEE")
    if association.is_established:
        print("Association established")
        status = association.send_c_store(dataset)
        # status = association.send_c_find(dataset)
        # Check the status of the operation
        if status:
            status_code = getattr(status, "Status", None)
            if status_code == 0x0000:
                print("DICOM file sent successfully")
            else:
                print(f"Failed to send DICOM file. Status: {hex(status_code) if status_code else 'Unknown'}")
        association.release()
    else:
        print("Association rejected, testing ABORT")
        association.abort()
else:
    print(f"DICOM file not found: {dicom_file_path}")