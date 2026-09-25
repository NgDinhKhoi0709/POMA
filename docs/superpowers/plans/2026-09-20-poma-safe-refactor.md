# POMA Safe Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Làm cho source POMA dễ thay đổi và dễ kiểm thử hơn mà không thay đổi CLI, trace schema, output prediction hoặc các con số evaluation đã dùng trong luận văn.

**Architecture:** Refactor theo hướng tạo các module sâu với interface nhỏ. Domain và table logic không phụ thuộc provider LLM, CLI/runtime không nằm trong pipeline core, còn `evaluation` chỉ tiêu thụ prediction/reference thay vì trở thành dependency của domain. Các bước di chuyển dùng compatibility re-export trong thời gian chuyển tiếp; việc chẻ `pipeline.py` chỉ thực hiện khi có lợi ích kiểm chứng được, không coi đó là điều kiện bắt buộc.

**Tech Stack:** Python 3.9+, Conda environment `kltn`, pytest, JSON/JSONL fixtures, OpenAI/OpenRouter/local LLM adapters hiện có, Git trên Windows.

**Spec:** `AGENTS.md` và đánh giá refactor trong cuộc hội thoại ngày 2026-09-20.

## Global Constraints

- Dùng Conda environment `kltn`; không tạo virtual environment mới.
- Giữ Python 3.9+ và PEP 8, bốn khoảng trắng, type hints cho public interface.
- Unit/integration tests không gọi LLM thật; dùng fake transport hoặc fake structured client.
- Không commit `.env`, API key, cache, generated `outputs/`, checkpoint hoặc dataset artifact chưa được xác nhận là source.
- Không dùng `git reset --hard`, `git checkout --` hoặc thao tác xóa/move đệ quy khi chưa xác minh target.
- Không thay đổi prompt, normalization policy, candidate policy, metric formula hoặc output schema trong cùng commit với mechanical move.
- Mỗi task kết thúc bằng một commit nhỏ, build/test độc lập và có message Conventional Commit.
- Giữ compatibility cho import/câu lệnh hiện tại cho đến khi tất cả call site đã chuyển và một task dọn dẹp riêng được review.
- Không chạy `git add --renormalize` cùng với move module; line-ending normalization là commit độc lập.
- Không dùng `git add tests`, `git add src` hoặc `git add -A` trong worktree dirty; stage đúng danh sách file đã review và kiểm tra `git diff --cached` trước mỗi commit.

## Review Focus

- **Test discovery/import:** pytest phải collect được toàn bộ test; SyntaxError ở `scripts/run_sea_lion_kaggle_eval.py` không được che khuất bằng cách loại test. Test thuộc Task 0.
- **Metric normalization/candidate choice:** thay đổi Unicode, whitespace, `Null`, `nul`, `none`, `n/a`, candidate không đứng đầu, list/order hoặc partial overlap không được làm lệch golden EM/F1/ROUGE-1/METEOR. Test thuộc Task 1 và Task 4.
- **Prompt contract:** quyết định rõ prompt compact hiện tại hay các assertion cũ là chuẩn trước khi refactor; test prompt phải phản ánh quyết định đã ghi lại. Test thuộc Task 0.
- **Trace/resume:** stage-resume với trace thiếu bước, trace lỗi hoặc trace từ hint source khác phải cho cùng lỗi có cấu trúc, không silently chạy sai stage. Test thuộc Task 5.
- **CLI/working-tree safety:** `run_poma.py`, `run_eval.py`, baseline runner và worktree Git `.worktrees/sea-lion-kaggle-poma/` không được bị ảnh hưởng ngoài phạm vi đã ghi; test smoke, status riêng của worktree và inventory thuộc Task 0/2/5.

## Current Boundaries and Files

Các điểm cần giữ nguyên hành vi trong lúc refactor:

- [`run_poma.py`](../../../run_poma.py): entry point hiện chứa dataset loading, `process_one`, batch workers, resume trace, persistence, reporting và auto-evaluation.
- [`src/orchestration/pipeline.py`](../../../src/orchestration/pipeline.py): stage refiner → specialists → normalization, prior trace loading, specialist registry và error trace.
- [`src/services/llm_client.py`](../../../src/services/llm_client.py): agent-facing LLM interface; hiện import transport từ `baseline.llm_client`.
- [`evaluation/normalization.py`](../../../evaluation/normalization.py): được scorer và core agent cùng dùng; đây là metric-sensitive code.
- [`preprocessing/loader.py`](../../../preprocessing/loader.py), [`src/contracts/finalization.py`](../../../src/contracts/finalization.py), [`src/agents/answer_normalization.py`](../../../src/agents/answer_normalization.py): các dependency ngược vào evaluation cần được giải quyết.
- [`scripts/run_sea_lion_kaggle_eval.py`](../../../scripts/run_sea_lion_kaggle_eval.py): hiện có SyntaxError tại argument `--limit` trong working tree.

Mục tiêu cấu trúc sau các task cần thiết:

```text
src/
  domain/          # contracts, answer/text policy, errors; không I/O/provider
  table/           # table parsing, representation, reduction
  llm/             # provider-neutral port và adapters
  pipeline/        # orchestration core và specialist registry
  runtime/         # dataset, batch, persistence, reporting, CLI helpers
  evaluation/      # metric/alignment/reporting (có thể giữ package root ở giai đoạn đầu)
  finalization/     # final answer workflow
  integrations/    # Kaggle/third-party integration
```

Không tạo toàn bộ cây thư mục trên một lần. Mỗi task chỉ tạo seam cần cho deliverable của task đó.

---

### Task 0: Safety snapshot, test discovery và quyết định baseline

**Files:**
- Create: `docs/refactor/worktree-inventory.md`
- Create: `pytest.ini`
- Create: `.gitattributes`
- Modify: `scripts/run_sea_lion_kaggle_eval.py:23`
- Modify: `tests/services/test_compact_prompts.py` và các test đang fail sau khi đã chốt prompt contract
- Test: toàn bộ `tests/` qua pytest collection và smoke suite

**Interfaces:**
- Consumes: trạng thái dirty hiện tại của Git, source/test/prompt đang có.
- Produces: test command ổn định, inventory dirty worktree, và quyết định rõ expected behavior của prompt.

- [ ] **Step 1: Ghi inventory trước khi chỉnh file**

  Chạy và lưu kết quả vào `docs/refactor/worktree-inventory.md`:

  ```powershell
  New-Item -ItemType Directory -Force .codex_tmp | Out-Null
  git status --short
  git branch --show-current
  git worktree list --porcelain
  git -C .worktrees/sea-lion-kaggle-poma status --short
  git diff --binary > .codex_tmp/refactor-working-tree.diff
  git diff --cached --binary > .codex_tmp/refactor-index.diff
  git ls-files --others --exclude-standard > .codex_tmp/refactor-untracked-files.txt
  rg --files checkpoints poma_v3lite reproductions outputs docs/research 2>$null
  ```

  Phân loại từng nhóm thành `source-candidate`, `research-artifact`, `generated-output`, hoặc `local-secret`; không stage `.env`, `outputs/`, checkpoints và PDF/DOCX nghiên cứu chỉ vì chúng xuất hiện trong status.

- [ ] **Step 2: Tạo branch an toàn và snapshot có chọn lọc**

  Tạo branch riêng để không sửa nhầm branch đang chạy luận văn:

  ```powershell
  git show-ref --verify --quiet refs/heads/codex/refactor-safety-2026-09-20
  if ($LASTEXITCODE -eq 0) {
      git switch codex/refactor-safety-2026-09-20
  } else {
      git switch -c codex/refactor-safety-2026-09-20
  }
  ```

  Commit chỉ các file source/test/docs đã được phân loại là code candidate; không dùng `git add -A`, `git add tests` hoặc `git add src`. Với mỗi untracked artifact cần bảo tồn nhưng chưa phù hợp để commit, ghi đường dẫn, `Get-FileHash -Algorithm SHA256 <path>` và phân loại vào inventory thay vì move hoặc xóa nó.

- [ ] **Step 3: Sửa SyntaxError tối thiểu và kiểm chứng riêng**

  Trong `scripts/run_sea_lion_kaggle_eval.py`, đổi:

  ```python
  parser.add_argument("--limit", type=int)``
  ```

  thành:

  ```python
  parser.add_argument("--limit", type=int)
  ```

  Chạy:

  ```powershell
  python -m py_compile scripts/run_sea_lion_kaggle_eval.py
  ```

  Expected: process exit code `0`.

- [ ] **Step 4: Khóa pytest discovery mà không che lỗi import**

  Tạo `pytest.ini`:

  ```ini
  [pytest]
  testpaths = tests
  python_files = test_*.py
  ```

  Chạy collection:

  ```powershell
  python -m pytest --collect-only -q -p no:cacheprovider
  ```

  Expected: không có SyntaxError/import error; test count được ghi vào inventory. Không dùng `--ignore` để làm xanh collection.

- [ ] **Step 5: Chốt compact prompt contract bằng diff và test**

  So sánh prompt hiện tại với các assertion trong `tests/services/test_compact_prompts.py`. Nếu prompt mới là chuẩn, sửa assertion để mô tả contract mới và thêm test cho nội dung bắt buộc; nếu test cũ là chuẩn, khôi phục prompt tương ứng trong một commit riêng. Ghi quyết định vào `docs/refactor/worktree-inventory.md` với lý do và danh sách file.

  Chạy tối thiểu:

  ```powershell
  python -m pytest tests/services/test_compact_prompts.py tests/agents/test_grounded_single_answer.py -q -p no:cacheprovider
  ```

  Expected: các failure được phân loại thành fixed behavior hoặc test bị thay đổi có lý do; không đánh dấu `xfail` chỉ để che mismatch.

- [ ] **Step 6: Thêm `.gitattributes` mà chưa renormalize**

  Tạo:

  ```gitattributes
  * text=auto eol=lf
  *.bat text eol=crlf
  *.cmd text eol=crlf
  *.ps1 text eol=crlf
  ```

  Chỉ kiểm tra `git diff --check`; chưa chạy `git add --renormalize .` trong task này.

- [ ] **Step 7: Chạy baseline suite và commit**

  ```powershell
  python -m pytest -q -p no:cacheprovider
  git diff --check
  git add pytest.ini .gitattributes scripts/run_sea_lion_kaggle_eval.py docs/refactor/worktree-inventory.md
  git add -p -- src/prompts src/prompts_compact tests/services/test_compact_prompts.py tests/agents/test_grounded_single_answer.py tests/baselines/test_structured_prompt_styles.py
  git diff --cached --check
  git diff --cached --name-only
  git commit -m "chore: establish safe refactor baseline"
  ```

  Expected: toàn bộ test hiện hành pass sau khi đã chốt prompt contract; test count và known external limitations được ghi lại, không ghi nhận “pass” nếu collection hoặc test fail.

---

### Task 1: Đóng băng metric path bằng golden fixture

**Files:**
- Create: `tests/fixtures/evaluation/golden_qas.json`
- Create: `tests/fixtures/evaluation/golden_predictions.json`
- Create: `tests/fixtures/evaluation/golden_expected_metrics.json`
- Create: `tests/evaluation/test_golden_metrics.py`
- Modify: không đổi implementation metric trong task này

**Interfaces:**
- Consumes: `evaluation.run.evaluate_files(prediction_path, qas_path, metrics=("f1", "em", "rouge1", "meteor"), strict=True)`.
- Produces: test fail nếu normalization/candidate alignment làm thay đổi output metric.

- [ ] **Step 1: Tạo fixture nhỏ có các trường hợp nhạy cảm**

  `golden_qas.json` phải chứa bốn record:

  ```json
  [
    {"qa_id": "gold-1", "table_id": "t1", "question": "Thành phố nào?", "answer": "Hà Nội", "hints": ["What"]},
    {"qa_id": "gold-2", "table_id": "t1", "question": "Có câu trả lời không?", "answer": "Null", "hints": ["YesNo"]},
    {"qa_id": "gold-3", "table_id": "t1", "question": "Giá trị?", "answer": "42", "hints": ["What"]},
    {"qa_id": "gold-4", "table_id": "t1", "question": "Địa danh?", "answer": "Hồ Chí Minh", "hints": ["What"]}
  ]
  ```

  `golden_predictions.json` phải chứa cùng IDs, candidate đúng ở vị trí thứ hai và một câu trả lời partial:

  ```json
  [
    {"qa_id": "gold-1", "prediction": ["Đà Nẵng", "  Hà Nội  "]},
    {"qa_id": "gold-2", "prediction": [" NUL "]},
    {"qa_id": "gold-3", "prediction": [" 42 "]},
    {"qa_id": "gold-4", "prediction": ["Hồ Chí"]}
  ]
  ```

- [ ] **Step 2: Viết test chỉ assert report ổn định, không assert hash provenance**

  ```python
  import json
  from pathlib import Path
  from evaluation.run import evaluate_files


  def test_golden_default_metrics_are_stable():
      root = Path(__file__).parents[1] / "fixtures" / "evaluation"
      report = evaluate_files(
          root / "golden_predictions.json",
          root / "golden_qas.json",
          metrics=("f1", "em", "rouge1", "meteor"),
          strict=True,
      )

      expected = json.loads((root / "golden_expected_metrics.json").read_text(encoding="utf-8"))
      assert report["metrics"] == expected
      assert report["coverage"]["evaluated_ids"] == ["gold-1", "gold-2", "gold-3", "gold-4"]
      assert report["coverage"]["missing_predictions"] == []
      assert report["coverage"]["extra_predictions"] == []
      assert report["source_candidate_statistics"]["max"] == 2
      assert report["evaluated_candidate_statistics"]["max"] == 2
  ```

  Tạo `golden_expected_metrics.json` một lần bằng evaluator hiện tại, review nội dung rồi commit như fixture bất biến:

  ```powershell
  python -c "import json; from evaluation.run import evaluate_files; from pathlib import Path; root=Path('tests/fixtures/evaluation'); report=evaluate_files(root/'golden_predictions.json', root/'golden_qas.json', metrics=('f1','em','rouge1','meteor'), strict=True); (root/'golden_expected_metrics.json').write_text(json.dumps(report['metrics'], ensure_ascii=False, indent=2), encoding='utf-8')"
  Get-Content tests/fixtures/evaluation/golden_expected_metrics.json
  ```

- [ ] **Step 3: Chạy test trước khi refactor normalization**

  ```powershell
  python -m pytest tests/evaluation/test_golden_metrics.py -q -p no:cacheprovider
  ```

  Expected: PASS. Fixture expected là output của scorer trước refactor; không sửa scorer hoặc golden expected để che khác biệt sau Task 4.

- [ ] **Step 4: Commit fixture độc lập**

  ```powershell
  git add tests/fixtures/evaluation/golden_qas.json tests/fixtures/evaluation/golden_predictions.json tests/fixtures/evaluation/golden_expected_metrics.json tests/evaluation/test_golden_metrics.py
  git commit -m "test: freeze default evaluation metrics"
  ```

---

### Task 2: Cô lập research artifacts và quyết định số phận worktree

**Files:**
- Create: `docs/refactor/research-artifact-policy.md`
- Modify: `.gitignore` nếu inventory xác nhận cần ignore pattern cụ thể
- Modify: `docs/refactor/worktree-inventory.md`
- Do not move/delete: `.worktrees/sea-lion-kaggle-poma/`, `checkpoints/`, `outputs/`, `reproductions/` trong cùng task

**Interfaces:**
- Consumes: inventory từ Task 0.
- Produces: policy rõ ràng để core runtime không import research code; không làm mất dữ liệu chưa commit.

- [ ] **Step 1: Kiểm tra worktree và dependency thực tế**

  ```powershell
  git worktree list
  git -C .worktrees/sea-lion-kaggle-poma status --short
  git -C .worktrees/sea-lion-kaggle-poma branch --show-current
  rg -n "sea-lion-kaggle-poma|poma_v3lite|reproductions|checkpoints" src scripts tests run_poma.py README.md
  ```

  Ghi branch, HEAD commit và trạng thái dirty của worktree. Nếu còn dùng, giữ nguyên và ghi commit/ref mà worker đó tiếp tục dùng; không giả định main refactor tự xuất hiện ở worktree. Nếu stale, chỉ archive sau khi có bản sao/hash và approval riêng.

- [ ] **Step 2: Viết policy phân loại**

  `docs/refactor/research-artifact-policy.md` phải quy định:

  - `src/`, `preprocessing/`, `evaluation/`, `baseline/`, `baselines/`, `tests/` là source/test cần review.
  - `outputs/`, `checkpoints/`, `.codex_tmp/` là generated/local và không stage.
  - `docs/research/`, `reproductions/`, `poma_v3lite/`, `scripts/analyze_*`, `scripts/build_*`, `scripts/run_d0*` là research/experiment; chỉ đưa vào commit khi có mục tiêu reproducibility cụ thể.
  - `scripts/` có thể giữ CLI nhưng không được import ngược vào `src/`.

- [ ] **Step 3: Thêm import-direction check**

  Tạo test `tests/test_import_direction.py` kiểm tra source file dưới `src/` không chứa import từ `scripts`, `outputs`, `checkpoints`, `reproductions`, hoặc `poma_v3lite`.

  ```python
  import ast
  from pathlib import Path


  def test_core_does_not_import_experiment_paths():
      forbidden = ("scripts", "outputs", "checkpoints", "reproductions", "poma_v3lite")
      for path in Path("src").rglob("*.py"):
          tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
          imported = []
          for node in ast.walk(tree):
              if isinstance(node, ast.Import):
                  imported.extend(alias.name for alias in node.names)
              elif isinstance(node, ast.ImportFrom) and node.module:
                  imported.append(node.module)
          assert not any(name == root or name.startswith(root + ".") for name in imported for root in forbidden), path
  ```

- [ ] **Step 4: Commit policy only**

  ```powershell
  python -m pytest tests/test_import_direction.py -q -p no:cacheprovider
  git add docs/refactor/research-artifact-policy.md docs/refactor/worktree-inventory.md tests/test_import_direction.py .gitignore
  git commit -m "docs: classify research and generated artifacts"
  ```

---

### Task 3: Tách LLM transport khỏi `baseline`

**Files:**
- Create: `src/llm/__init__.py`
- Create: `src/llm/ports.py`
- Create: `src/llm/transport.py`
- Modify: `src/services/llm_client.py`
- Modify: `baseline/llm_client.py` to re-export compatibility names or delegate to `src.llm.transport`
- Test: `tests/services/test_llm_transport.py`, existing `tests/services/test_llm_client_structured.py`, `tests/services/test_openrouter_structured_transport.py`

**Interfaces:**
- Consumes: existing provider behavior from `baseline.llm_client.LLMZeroShotClient.generate_with_usage`.
- Produces: provider-neutral `TextTransport` protocol and one compatibility adapter.

  ```python
  from typing import Any, Mapping, Protocol


  class TextTransport(Protocol):
      def generate_with_usage(
          self,
          model: str,
          prompt: str,
          config: Any,
          *,
          max_retries: int,
          retry_delay: int,
      ) -> tuple[str, Mapping[str, Any]]: ...
  ```

- [ ] **Step 1: Write fake transport contract test**

  Test fake trả raw text và usage; test `LLMClient` có thể nhận transport qua constructor hoặc factory mà không import `baseline` trong module implementation. Thêm hai regression tests: hai `LLMClient()` với model remote dùng cùng shared provider client; model `local/` không gọi provider transport và vẫn dùng local client.

- [ ] **Step 2: Implement transport module bằng code hiện có**

  Di chuyển phần provider-neutral `GenConfig`, model parsing, usage normalization và retry cần thiết sang `src/llm/transport.py`. Giữ provider-specific HTTP code trong adapter; không đổi payload, timeout, retry count hoặc cost calculation.

  Adapter tối thiểu phải giữ nguyên lời gọi hiện tại:

  ```python
  class ProviderTextTransport:
      def __init__(self, client):
          self._client = client

      def generate_with_usage(
          self, model, prompt, config, *, max_retries, retry_delay
      ):
          return self._client.generate_with_usage(
              model,
              prompt,
              config,
              max_retries=max_retries,
              retry_delay=retry_delay,
          )
  ```

- [ ] **Step 3: Inject transport vào `LLMClient`**

  Giữ constructor tương thích:

  ```python
  class LLMClient:
      def __init__(self, config=None, *, transport=None, local_client=None):
          self._transport = transport or build_default_transport()
  ```

  Default factory được phép tạo adapter production; tests truyền fake. Local backend vẫn đi qua adapter local hiện có.

- [ ] **Step 4: Giữ compatibility cho baseline**

  `baseline/llm_client.py` re-export `GenConfig`, `LLMZeroShotClient`, `parse_model_spec` từ module mới hoặc dùng adapter mỏng. Không để `src/services/llm_client.py` import ngược từ `baseline`.

- [ ] **Step 5: Chạy regression test và kiểm tra import direction**

  ```powershell
  python -m pytest tests/services tests/baselines -q -p no:cacheprovider
  rg -n "from baseline\.llm_client|import baseline\.llm_client" src
  ```

  Expected: không còn match trong `src/`; structured output, usage totals, repair attempt, shared-client caching, local backend và provider config giữ nguyên.

- [ ] **Step 6: Commit**

  ```powershell
  git add src/llm src/services/llm_client.py baseline/llm_client.py tests/services/test_llm_transport.py tests/services/test_llm_client_structured.py
  git commit -m "refactor: isolate llm transport from baselines"
  ```

---

### Task 4: Tách normalization policy dùng chung nhưng giữ evaluation facade

**Files:**
- Create: `src/domain/__init__.py`
- Create: `src/domain/text_normalization.py`
- Modify: `evaluation/normalization.py`
- Modify: `src/agents/answer_normalization.py`
- Modify: `src/agents/grounded_single_answer.py`
- Modify: `src/contracts/finalization.py`
- Modify: `preprocessing/loader.py`
- Modify: `evaluation/f1.py`, `evaluation/exact_match.py`, `evaluation/rouge1.py`, `evaluation/meteor.py` only where import path changes
- Test: `tests/domain/test_text_normalization.py`, `tests/evaluation/test_golden_metrics.py`, existing normalization-related tests

**Interfaces:**
- Consumes: behavior currently exposed by `evaluation.normalization`.
- Produces: domain interface:

  ```python
  def normalize_text(text: Any, *, use_vietnamese_tokenization: bool = False) -> str: ...
  def is_unanswerable_reference(answer: Any) -> bool: ...
  def is_unanswerable_prediction(answer: Any, *, use_vietnamese_tokenization: bool = False) -> bool: ...
  def prediction_is_unanswerable(candidates: Iterable[str], *, use_vietnamese_tokenization: bool = False) -> bool: ...
  ```

- [ ] **Step 1: Add characterization tests for current policy**

  Pin exact results for `None`, Unicode NFC Vietnamese text, leading/trailing whitespace, `Null`, `nul`, `none`, `n/a`, `na`, and `không thể trả lời`. Include a test proving `src.table_executor.ast_executor.normalize_text` remains separate because it uses NFKC/table parsing semantics.

- [ ] **Step 2: Implement domain module by moving, not rewriting**

  Copy the current function bodies byte-for-byte where possible. Do not combine the domain normalizer with table executor normalizer. Add return annotations and docstrings only.

- [ ] **Step 3: Turn evaluation module into compatibility facade**

  In `evaluation/normalization.py`, import/re-export the four shared functions from `src.domain.text_normalization`, leaving evaluation-only functions such as `exact_text_match`, list matching and variant policy in place.

  ```python
  from src.domain.text_normalization import (
      is_unanswerable_prediction,
      is_unanswerable_reference,
      normalize_text,
      prediction_is_unanswerable,
  )
  ```

- [ ] **Step 4: Update consumers one group at a time**

  Update agents/contracts/preprocessing first, then metric modules. After each group run its focused tests and `rg` to confirm no accidental import cycle.

- [ ] **Step 5: Run golden and full metric tests before/after comparison**

  ```powershell
  python -m pytest tests/domain tests/evaluation -q -p no:cacheprovider
  python -m pytest -q -p no:cacheprovider
  ```

  Expected: golden report remains identical except provenance `scorer_sha256`, which is intentionally source-dependent and must not be asserted as a fixed value.

- [ ] **Step 6: Commit**

  ```powershell
  git add src/domain evaluation/normalization.py evaluation/f1.py evaluation/exact_match.py evaluation/rouge1.py evaluation/meteor.py src/agents/answer_normalization.py src/agents/grounded_single_answer.py src/contracts/finalization.py preprocessing/loader.py tests/domain tests/evaluation
  git commit -m "refactor: move shared answer normalization into domain"
  ```

---

### Task 5: Tách runtime batch khỏi `run_poma.py`

**Files:**
- Create: `src/runtime/__init__.py`
- Create: `src/runtime/dataset.py`
- Create: `src/runtime/result_store.py`
- Create: `src/runtime/batch.py`
- Create: `src/runtime/reporting.py`
- Create: `src/runtime/evaluation_runner.py`
- Modify: `run_poma.py` to retain CLI compatibility wrappers
- Test: `tests/runtime/test_dataset.py`, `tests/runtime/test_result_store.py`, `tests/runtime/test_batch.py`, `tests/runtime/test_evaluation_runner.py`, existing `tests/test_run_poma_artifacts.py`

**Interfaces:**
- `DatasetRepository.load_pair(qas_path: Path, tables_path: Path) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]`
- `ResultStore.load_records(path: Path) -> list[dict[str, Any]]`
- `ResultStore.save_records(records: Sequence[Mapping[str, Any]], path: Path) -> None`
- `BatchConfig` dataclass chứa `qas_path`, `tables_path`, `output_path`, `traces_path`, `limit`, `workers`, `stages`, `skip_existing`, `auto_evaluate`, `hint_predictions_path`.
- `BatchRunner(process_one_fn: Callable[..., dict[str, Any]], result_store: ResultStore, reporter: RunReporter, evaluation_runner: EvaluationRunner).run(config: BatchConfig) -> list[dict[str, Any]]`
- `RunReporter.print_result(record: Mapping[str, Any], index: int, total: int) -> None`
- `RunReporter.print_summary(records: Sequence[Mapping[str, Any]]) -> None`
- `EvaluationRunner.evaluate_records(predictions: Sequence[Mapping[str, Any]], qas: Sequence[Mapping[str, Any]], *, metrics: Sequence[str] | None, fail_on_metric_error: bool) -> dict[str, Any]`
- `EvaluationRunner.evaluate_files(prediction_path: Path, qas_path: Path, *, tables_path: Path | None, output_path: Path | None, metrics: Sequence[str] | None, fail_on_metric_error: bool, candidate_policy: str, strict: bool, bif_config: BIFConfig | None, bif_details_path: Path | None) -> dict[str, object]`

- [ ] **Step 1: Viết tests cho dataset và result store trước khi move**

  Test wrapper JSON (`{"qas": [...]}`/list), table index theo `table_id`, JSON output UTF-8, merge trace theo `qa_id`, duplicate ID và missing file. Test chỉ dùng `tmp_path`.

- [ ] **Step 2: Di chuyển dataset helpers không đổi behavior**

  Chuyển `_load_json`, `load_dataset_pair`, `_get_table_str` vào `src/runtime/dataset.py`. Giữ `run_poma.load_dataset_pair` gọi lại implementation mới để import cũ vẫn chạy.

- [ ] **Step 3: Di chuyển persistence/resume helpers**

  Chuyển `_load_existing_results`, `_merge_records_by_qa_id`, `_build_trace_index`, `_merge_trace_lists`, `_save_results`, `_save_prediction_output`, `_save_stage_outputs` vào `ResultStore`. Giữ nguyên key `qa_id`, trace step names `1_question_refiner`, `2_router`, `3_specialists`, `4_answer_normalization`.

- [ ] **Step 4: Đóng gói batch options và di chuyển `run_batch`**

  Dùng dataclass thay cho chuỗi tham số dài; `run_poma.run_batch(...)` chỉ tạo `BatchConfig` rồi gọi `BatchRunner.run`. `process_one_fn` được inject để test batch không cần LLM. Không thay đổi thứ tự incremental save hoặc hành vi khi một worker fail.

  ```python
  @dataclass(frozen=True)
  class BatchConfig:
      qas_path: Path
      tables_path: Path
      output_path: Path | None = None
      traces_path: Path | None = None
      limit: int | None = None
      workers: int = 1
      stages: set[str] | None = None
      skip_existing: bool = True
      auto_evaluate: bool = True
      hint_predictions_path: Path | None = None
  ```

  `EvaluationRunner` phải được tạo trong Task 5 trước khi `BatchRunner` được move, vì auto-evaluation hiện tại của `run_batch` nhận records in-memory còn `run_eval.py` nhận file paths:

  ```python
  class EvaluationRunner:
      def evaluate_records(self, predictions, qas, *, metrics=None,
                           fail_on_metric_error=False):
          samples, _ = align_records(predictions, qas)
          return {"overall": _core_metrics(samples, set(metrics or DEFAULT_METRICS))}

      def evaluate_files(self, prediction_path, qas_path, **kwargs):
          return evaluate_files(prediction_path, qas_path, **kwargs)
  ```

- [ ] **Step 5: Viết regression test cho sequential/parallel/resume**

  Dùng fake `process_one`/fake pipeline để kiểm tra:

  - `workers=1` lưu record sau từng QA.
  - `workers>1` vẫn merge đủ records theo `qa_id`.
  - chạy `--stages normalization` đọc prior trace và không gọi refiner/specialist.
  - prior trace thiếu key trả `InputDataError` có `stage`/`qa_id`.
  - error trace được persist trước khi exception thoát.
  - `EvaluationRunner.evaluate_records` trả cùng `overall` metric shape như `_run_auto_evaluation` cũ cho cùng prediction/QAs fixture.

- [ ] **Step 6: Chạy CLI smoke và commit**

  ```powershell
  python -m pytest tests/runtime tests/test_run_poma_artifacts.py -q -p no:cacheprovider
  python run_poma.py --help
  git diff --check
  git add src/runtime/__init__.py src/runtime/dataset.py src/runtime/result_store.py src/runtime/batch.py src/runtime/reporting.py src/runtime/evaluation_runner.py run_poma.py tests/runtime/test_dataset.py tests/runtime/test_result_store.py tests/runtime/test_batch.py tests/runtime/test_evaluation_runner.py tests/test_run_poma_artifacts.py
  git commit -m "refactor: isolate poma batch runtime"
  ```

  Expected: help text, default output `outputs/poma/<qas-stem>.json`, trace naming và public imports không đổi.

---

### Task 6: Làm mỏng evaluation CLI sau khi runtime adapter đã tồn tại

**Files:**
- Modify: `run_eval.py`, `run_poma.py`
- Modify: `evaluation/__init__.py` only for documented public exports
- Test: `tests/runtime/test_evaluation_runner.py`, `tests/evaluation/test_run.py`, `tests/test_run_poma_artifacts.py`

**Interfaces:**
- Consumes: `EvaluationRunner.evaluate_files(prediction_path: Path, qas_path: Path, *, tables_path: Path | None, output_path: Path | None, metrics: Sequence[str] | None, fail_on_metric_error: bool, candidate_policy: str, strict: bool, bif_config: BIFConfig | None, bif_details_path: Path | None) -> dict[str, object]` created in Task 5.
- `run_eval.py` remains a parser/exit-code adapter.

- [ ] **Step 1: Test CLI delegation and failure exit code**

  Mock `src.runtime.evaluation_runner.EvaluationRunner.evaluate_files`; assert parser forwards metrics, `fail_on_metric_error`, candidate policy, strict, complete `BIFConfig`, BIF details and output path. Assert `EvaluationDataError` returns non-zero without writing a partial report.

- [ ] **Step 2: Delegate CLI orchestration glue**

  Keep metric implementations in `evaluation/`; move no scorer in this task. `run_eval.py` constructs/uses the existing `EvaluationRunner` and writes the same JSON report.

  ```python
  report = EvaluationRunner().evaluate_files(
      Path(args.pred),
      Path(args.qas),
      tables_path=Path(args.tables) if args.tables else None,
      output_path=Path(args.output) if args.output else None,
      metrics=metrics,
      fail_on_metric_error=args.fail_on_metric_error,
      candidate_policy=args.candidate_policy,
      strict=args.strict,
      bif_config=bif_config,
      bif_details_path=Path(args.bif_details) if args.bif_details else None,
  )
  ```

- [ ] **Step 3: Verify output locations**

  ```powershell
  python -m pytest tests/runtime/test_evaluation_runner.py tests/evaluation/test_run.py -q -p no:cacheprovider
  python run_eval.py --help
  ```

- [ ] **Step 4: Commit**

  ```powershell
  git add run_eval.py evaluation/__init__.py tests/runtime/test_evaluation_runner.py tests/evaluation/test_run.py
  git commit -m "refactor: keep evaluation behind runtime adapter"
  ```

---

### Task 7: Quyết định có chẻ pipeline hay không (deferred gate)

**Files:**
- No file move by default.
- If the gate is met, create `src/pipeline/runner.py`, `src/pipeline/resume.py`, `src/pipeline/registry.py` and corresponding tests.
- Test: `tests/orchestration/test_pipeline_contract.py`, existing `tests/agents/*`, `tests/services/*`.

**Interfaces:**
- Candidate interface: `PipelineRunner(llm: LLMClient, executor: ParallelExecutor).run(request: QARequest, *, stages: set[str] | None = None, prior_trace: dict[str, Any] | None = None) -> dict[str, Any]`.

- [ ] **Step 1: Measure whether current pipeline is actually blocking work**

  Ghi một issue/decision record nếu ít nhất một điều đúng: pipeline cần thêm stage độc lập; resume logic cần test riêng nhưng không thể test qua public seam; hoặc provider/executor cần thay thế trong nhiều hơn một use case.

- [ ] **Step 2: Nếu gate chưa đạt, đóng task bằng decision record**

  Ghi rõ `src/orchestration/pipeline.py` được giữ nguyên vì đang chạy end-to-end và chưa có hai adapter/consumer cần seam mới. Chạy full suite rồi commit docs-only.

- [ ] **Step 3: Nếu gate đạt, viết contract test trước**

  Test cùng một request qua fake LLM/executor cho full run, refiner-only, specialists-only, normalization-only, prior trace và structured error. Chỉ sau khi test pass mới tách implementation.

- [ ] **Step 4: Commit theo lựa chọn**

  ```powershell
  git commit -m "docs: defer pipeline split until a seam is justified"
  ```

  hoặc:

  ```powershell
  git commit -m "refactor: isolate pipeline runner and resume logic"
  ```

---

### Task 8: Final verification và dọn compatibility có kiểm soát

**Files:**
- Modify: `README.md` để cập nhật architecture/import guidance
- Modify: `AGENTS.md` nếu command/test path đã thay đổi
- Delete only after import audit: obsolete compatibility wrappers
- Test: toàn bộ `tests/`, CLI smoke tests, import-direction check

**Interfaces:**
- Consumes: tất cả public compatibility exports từ Task 3–6.
- Produces: source tree/documentation nhất quán, không còn dependency ngược đã chẩn đoán.

- [ ] **Step 1: Chạy import audit**

  ```powershell
  rg -n "from baseline\.llm_client|from evaluation\.normalization|from scripts|from outputs|from checkpoints" src preprocessing
  ```

  Cho phép `evaluation/normalization.py` re-export domain trong giai đoạn chuyển tiếp; không cho phép core import `scripts`, `outputs`, `checkpoints`.

- [ ] **Step 2: Chạy toàn bộ verification**

  ```powershell
  python -m pytest -q -p no:cacheprovider
  python -m pytest --collect-only -q -p no:cacheprovider
  python run_poma.py --help
  python run_eval.py --help
  python scripts/run_baseline.py --help
  git diff --check
  ```

  Expected: test count không giảm ngoài test bị thay thế có decision record; golden metric pass; CLI help pass; không có warning line-ending làm bẩn diff.

- [ ] **Step 3: Cập nhật README architecture và migration note**

  Ghi rõ output paths, public imports được hỗ trợ, cách chạy test, và việc `pipeline.py` được split hay deferred. Không mô tả package chưa tồn tại.

- [ ] **Step 4: Xóa compatibility wrapper chỉ khi không còn caller**

  Dùng `rg` trên toàn repo và chạy full suite trước khi xóa. Mỗi deletion là commit riêng với message `refactor: remove obsolete compatibility wrapper`.

- [ ] **Step 5: Tạo final refactor report**

  Ghi các metric golden trước/sau, test count, remaining dirty artifacts, worktree status và các việc cố ý deferred. Không commit generated outputs.

---

## Rollback and Stop Conditions

- Nếu Task 0 không đạt collection sạch: dừng, không move module.
- Nếu golden metrics lệch sau Task 4: giữ commit test/fixture, revert riêng implementation move bằng Git revert; không sửa expected values để làm xanh.
- Nếu import cycle xuất hiện sau Task 3 hoặc Task 4: giữ compatibility facade, tách domain module nhỏ hơn; không thêm import động vào CLI để che cycle.
- Nếu `.worktrees/sea-lion-kaggle-poma/` còn chạy workflow quan trọng: không archive/xóa; cập nhật policy và tạo lại worktree sau khi branch/ref ổn định.
- Nếu mechanical move tạo line-ending diff lớn: dừng move, commit `.gitattributes` riêng, xử lý normalization trong task độc lập.

## Definition of Done

- Baseline test collection chạy được và test failures đã được phân loại có quyết định.
- Có golden evaluation fixture bảo vệ default metric path.
- `src/services/llm_client.py` không còn phụ thuộc vào `baseline.llm_client`.
- Core domain không phụ thuộc `evaluation` để lấy normalization policy.
- `run_poma.py` trở thành CLI compatibility layer mỏng hơn; batch/persistence có test interface riêng.
- Research artifacts và `.worktrees` có policy rõ, không bị xóa ngoài phạm vi.
- CLI cũ, output paths, trace keys và prediction schema vẫn tương thích.
- `pipeline.py` chỉ bị chẻ khi có seam được chứng minh bằng test và ít nhất hai consumer/adapter hợp lý.
