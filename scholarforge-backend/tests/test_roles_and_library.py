import pytest
import uuid
from httpx import AsyncClient
from app.models.paper import Paper, PaperStatus
from app.models.knowledge_graph import GraphNode, GraphEdge
from app.models.literature_review import LiteratureReview

@pytest.mark.asyncio
async def test_all_user_roles(client: AsyncClient):
    roles = ["student", "researcher", "professor", "reviewer", "guest"]
    for role in roles:
        email = f"{role}@example.com"
        reg_res = await client.post(
            "/api/v1/auth/register",
            json={
                "name": f"Dr. {role.capitalize()}",
                "email": email,
                "password": "SecurePassword123!",
                "role": role
            }
        )
        assert reg_res.status_code == 200, f"Registration failed for role {role}: {reg_res.text}"
        user_data = reg_res.json()
        assert user_data["role"] == role
        assert user_data["name"] == f"Dr. {role.capitalize()}"

        # Test login
        login_res = await client.post(
            "/api/v1/auth/login",
            data={
                "username": email,
                "password": "SecurePassword123!"
            }
        )
        assert login_res.status_code == 200, f"Login failed for role {role}: {login_res.text}"
        token_data = login_res.json()
        assert "access_token" in token_data
        assert token_data["role"] == role
        assert token_data["name"] == f"Dr. {role.capitalize()}"

        # Test /auth/me returns name and role
        me_res = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token_data['access_token']}"}
        )
        assert me_res.status_code == 200
        me_data = me_res.json()
        assert me_data["role"] == role
        assert me_data["name"] == f"Dr. {role.capitalize()}"

    # Verify admin signup is prohibited (only login allowed for admin)
    admin_reg = await client.post(
        "/api/v1/auth/register",
        json={
            "name": "Admin Test",
            "email": "admin_test_reg@example.com",
            "password": "SecurePassword123!",
            "role": "admin"
        }
    )
    assert admin_reg.status_code == 400
    assert "Admin accounts cannot be registered" in admin_reg.json()["detail"]

@pytest.mark.asyncio
async def test_paper_library_and_keyword_search(client: AsyncClient, db_session):
    # Register and login user
    reg = await client.post(
        "/api/v1/auth/register",
        json={"name": "Alice Professor", "email": "prof@test.com", "password": "pass", "role": "professor"}
    )
    user_id = uuid.UUID(reg.json()["id"])
    login = await client.post("/api/v1/auth/login", data={"username": "prof@test.com", "password": "pass"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Add sample papers in DB
    p1 = Paper(
        id=uuid.uuid4(),
        user_id=user_id,
        title="Attention Is All You Need (Transformers)",
        authors=["Vaswani", "Shazeer"],
        category="Deep Learning",
        file_path="/tmp/p1.pdf",
        status=PaperStatus.processed
    )
    p2 = Paper(
        id=uuid.uuid4(),
        user_id=user_id,
        title="BERT: Pre-training of Deep Bidirectional Transformers",
        authors=["Devlin", "Chang"],
        category="Natural Language Processing",
        file_path="/tmp/p2.pdf",
        status=PaperStatus.processed
    )
    p3 = Paper(
        id=uuid.uuid4(),
        user_id=user_id,
        title="Deep Residual Learning for Image Recognition",
        authors=["He", "Zhang"],
        category="Computer Vision",
        file_path="/tmp/p3.pdf",
        status=PaperStatus.processed
    )
    db_session.add_all([p1, p2, p3])
    await db_session.commit()

    # 1. Fetch all papers
    res_all = await client.get("/api/v1/papers/", headers=headers)
    assert res_all.status_code == 200
    papers_all = res_all.json()
    assert len(papers_all) == 3

    # 2. Search keyword: "BERT"
    res_bert = await client.get("/api/v1/papers/?query=BERT", headers=headers)
    assert res_bert.status_code == 200
    papers_bert = res_bert.json()
    assert len(papers_bert) == 1
    assert "BERT" in papers_bert[0]["title"]

    # 3. Search keyword: "Transformer" (matches both Attention and BERT)
    res_trans = await client.get("/api/v1/papers/?query=Transformer", headers=headers)
    assert res_trans.status_code == 200
    papers_trans = res_trans.json()
    assert len(papers_trans) == 2

    # 4. Search non-existent keyword
    res_none = await client.get("/api/v1/papers/?query=QuantumMechanics", headers=headers)
    assert res_none.status_code == 200
    assert len(res_none.json()) == 0

@pytest.mark.asyncio
async def test_knowledge_graph_endpoints(client: AsyncClient, db_session):
    # Register and login
    reg = await client.post(
        "/api/v1/auth/register",
        json={"name": "Researcher Bob", "email": "bob@test.com", "password": "pass", "role": "researcher"}
    )
    user_id = uuid.UUID(reg.json()["id"])
    login = await client.post("/api/v1/auth/login", data={"username": "bob@test.com", "password": "pass"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    paper_id = uuid.uuid4()
    p = Paper(
        id=paper_id,
        user_id=user_id,
        title="Graph Neural Networks in Molecular Biology",
        authors=["Alice Smith", "Bob Jones"],
        abstract="We use deep learning and graph neural networks to analyze molecular graphs.",
        category="Bioinformatics",
        file_path="/tmp/gnn.pdf",
        status=PaperStatus.processed
    )
    db_session.add(p)
    await db_session.commit()

    # 1. Test /knowledge-graph/all
    all_graph = await client.get("/api/v1/knowledge-graph/all", headers=headers)
    assert all_graph.status_code == 200
    graph_data = all_graph.json()
    assert "nodes" in graph_data
    assert "edges" in graph_data
    assert len(graph_data["nodes"]) > 0
    # Check paper node is present
    paper_nodes = [n for n in graph_data["nodes"] if n["id"] == f"paper_{paper_id}"]
    assert len(paper_nodes) == 1
    # Check author / methodology / domain nodes exist
    labels = set([n["labels"][0] for n in graph_data["nodes"]])
    assert "Paper" in labels

    # 2. Test /knowledge-graph/paper/{paper_id}
    p_graph = await client.get(f"/api/v1/knowledge-graph/paper/{paper_id}", headers=headers)
    assert p_graph.status_code == 200
    assert len(p_graph.json()["nodes"]) > 0

    # 3. Test /knowledge-graph/overview
    overview = await client.get("/api/v1/knowledge-graph/overview", headers=headers)
    assert overview.status_code == 200
    ov_data = overview.json()
    assert "top_authors" in ov_data

@pytest.mark.asyncio
async def test_agent_result_caching_and_batch_consistency(client: AsyncClient, db_session):
    reg = await client.post(
        "/api/v1/auth/register",
        json={"name": "Dr. Reviewer", "email": "rev@test.com", "password": "pass", "role": "reviewer"}
    )
    user_id = uuid.UUID(reg.json()["id"])
    login = await client.post("/api/v1/auth/login", data={"username": "rev@test.com", "password": "pass"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    pid1 = uuid.uuid4()
    pid2 = uuid.uuid4()
    p1 = Paper(id=pid1, user_id=user_id, title="Paper Alpha", authors=["A. Author"], file_path="/p1.pdf", status=PaperStatus.processed)
    p2 = Paper(id=pid2, user_id=user_id, title="Paper Beta", authors=["B. Author"], file_path="/p2.pdf", status=PaperStatus.processed)
    
    # Pre-populate saved literature review for batch [pid1, pid2]
    lr = LiteratureReview(
        id=uuid.uuid4(),
        user_id=user_id,
        paper_ids=[str(pid1), str(pid2)],
        summary="Comprehensive comparative summary of Alpha and Beta.",
        key_findings=["Alpha achieves 95%", "Beta improves speed by 2x"],
        contributions=["New architecture", "Novel benchmark"],
        comparative_review="Alpha focuses on accuracy while Beta prioritizes latency.",
        paper_reviews=[
            {"paper_id": str(pid1), "title": "Paper Alpha", "summary": "Alpha summary"},
            {"paper_id": str(pid2), "title": "Paper Beta", "summary": "Beta summary"}
        ]
    )
    db_session.add_all([p1, p2, lr])
    await db_session.commit()

    # Query Literature Review result for [pid1, pid2]
    lr_res = await client.get(
        f"/api/v1/agents/literature-review/result?paper_ids={pid1}&paper_ids={pid2}",
        headers=headers
    )
    assert lr_res.status_code == 200
    data = lr_res.json()["result"]
    assert "Comprehensive comparative summary" in data["summary"]
    assert data["comparative_review"] is not None
    assert len(data["paper_reviews"]) == 2

    # Querying a single paper [pid1] when only [pid1, pid2] was saved returns 404 (does NOT confuse batches)
    single_lr = await client.get(
        f"/api/v1/agents/literature-review/result?paper_ids={pid1}",
        headers=headers
    )
    assert single_lr.status_code == 404

@pytest.mark.asyncio
async def test_admin_paper_controls_and_moderation(client: AsyncClient, db_session):
    from app.models.user import User, UserRole
    from app.core.security import get_password_hash

    # Create admin user directly in DB (simulating seeded admin)
    admin_id = uuid.uuid4()
    admin_user = User(
        id=admin_id,
        name="Admin Boss",
        email="admin_direct@test.com",
        password_hash=get_password_hash("AdminPass123!"),
        role=UserRole.admin,
        is_active=True
    )

    # Create normal researcher user
    student_id = uuid.uuid4()
    student_user = User(
        id=student_id,
        name="Student Sam",
        email="student_sam@test.com",
        password_hash=get_password_hash("StudentPass123!"),
        role=UserRole.student,
        is_active=True
    )

    paper_id = uuid.uuid4()
    paper = Paper(
        id=paper_id,
        user_id=student_id,
        title="Harmful Chemical Syntheses",
        authors=["Danger Author"],
        file_path="/tmp/harmful.pdf",
        status=PaperStatus.processed,
        is_flagged=False,
        is_available_for_ai=True
    )

    db_session.add_all([admin_user, student_user, paper])
    await db_session.commit()

    # Login as admin
    admin_login = await client.post("/api/v1/auth/login", data={"username": "admin_direct@test.com", "password": "AdminPass123!"})
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Admin views all uploaded papers across any user, along with author name, email and role
    all_papers_res = await client.get("/api/v1/papers/admin/all", headers=admin_headers)
    assert all_papers_res.status_code == 200
    all_papers = all_papers_res.json()
    assert len(all_papers) >= 1
    found = [p for p in all_papers if p["id"] == str(paper_id)]
    assert len(found) == 1
    assert found[0]["user_name"] == "Student Sam"
    assert found[0]["user_role"] == "student"
    assert found[0]["user_email"] == "student_sam@test.com"

    # 2. Admin flags paper as harmful / policy violation
    flag_res = await client.patch(
        f"/api/v1/papers/admin/{paper_id}/flag",
        json={"is_flagged": True, "flag_reason": "Harmful bio-chemical contents", "is_available_for_ai": False},
        headers=admin_headers
    )
    assert flag_res.status_code == 200
    flagged_data = flag_res.json()
    assert flagged_data["is_flagged"] is True
    assert flagged_data["is_available_for_ai"] is False
    assert flagged_data["flag_reason"] == "Harmful bio-chemical contents"

    # 3. Verify AI analysis is blocked on flagged / AI-disabled paper
    student_login = await client.post("/api/v1/auth/login", data={"username": "student_sam@test.com", "password": "StudentPass123!"})
    student_token = student_login.json()["access_token"]
    student_headers = {"Authorization": f"Bearer {student_token}"}

    blocked_ai = await client.post(
        "/api/v1/agents/literature-review",
        json={"paper_ids": [str(paper_id)], "parameters": {}},
        headers=student_headers
    )
    assert blocked_ai.status_code == 400
    assert "not available for AI analysis" in blocked_ai.json()["detail"]

    # 4. Admin deletes paper
    del_paper_res = await client.delete(f"/api/v1/papers/{paper_id}", headers=admin_headers)
    assert del_paper_res.status_code == 200

    # Verify paper is deleted
    p_check = await client.get(f"/api/v1/papers/{paper_id}", headers=admin_headers)
    assert p_check.status_code == 404

    # 5. Admin deletes user
    del_user_res = await client.delete(f"/api/v1/users/{student_id}", headers=admin_headers)
    assert del_user_res.status_code == 200

    u_check = await client.get(f"/api/v1/users/{student_id}", headers=admin_headers)
    assert u_check.status_code == 404
