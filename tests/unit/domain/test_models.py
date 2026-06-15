from data_analysis_agent.domain.models import Dataset, QueryRecord, AgentRunRecord


def test_dataset_defaults():
    ds = Dataset(filename="data.csv", file_path="/tmp/data.csv")
    assert ds.id is not None
    assert ds.column_names == []
    assert ds.row_count is None


def test_query_record_defaults():
    qr = QueryRecord(dataset_id="abc", question="What is the total?")
    assert qr.id is not None
    assert qr.status == "pending"
    assert qr.answer is None


def test_agent_run_record_defaults():
    run = AgentRunRecord(query_record_id="xyz")
    assert run.id is not None
    assert run.status == "pending"
