import pandas as pd
from eios.aml.mule_ring_detector import MuleRingDetector

def test_mule():
    df = pd.DataFrame({
        'source_id': [1, 2, 3],
        'target_id': [10, 10, 11],
        'edge_type': ['PAYMENT', 'PAYMENT', 'IP'],
        'is_shared_context': [False, False, False]
    })

    det = MuleRingDetector()
    clusters = det.detect_mule_rings(df)
    print(clusters)

test_mule()
