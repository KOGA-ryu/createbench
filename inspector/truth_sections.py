from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton

from core.node_resolution import resolve_node_state
from core.scene_resolution import resolve_scene_state


def _format_line_range(source):
    line_start = source.get("line_start")
    line_end = source.get("line_end")
    if line_start is None and line_end is None:
        return "-"
    if line_start == line_end or line_end is None:
        return str(line_start)
    if line_start is None:
        return str(line_end)
    return f"{line_start}-{line_end}"


def _count_snapshot_nodes(snapshot):
    return 1 + sum(_count_snapshot_nodes(child) for child in snapshot.get("children", []))


def _summarize_snapshot_children(snapshot):
    children = snapshot.get("children", [])
    if not children:
        return "-"
    summary: list[str] = []
    for child in children[:3]:
        child_name = child.get("name")
        child_type = child.get("type") or "unknown"
        summary.append(str(child_name or child_type))
    if len(children) > 3:
        summary.append("...")
    return ", ".join(summary)


def build_node_truth_section(layout, node, model, callbacks):
    metadata = getattr(node, "metadata", {}) or {}
    source = metadata.get("source", {})
    trust = metadata.get("trust", {})
    provenance = metadata.get("provenance", {})
    raw = metadata.get("raw", {})
    scene_metadata = getattr(model, "scene_metadata", {})
    resolved = resolve_node_state(node, scene_metadata)
    warnings = list(trust.get("warnings") or []) + list(provenance.get("packet_warnings") or [])

    layout.addWidget(QLabel("Truth"))
    if any([source, trust, provenance, raw, scene_metadata]):
        lines = [
            f"resolved_mode: {resolved['resolved_mode']}",
            f"editability: {resolved['editability']}",
            f"trust_level: {trust.get('trust_level') or '-'}",
            f"representation_origin: {provenance.get('representation_origin') or trust.get('representation_origin') or '-'}",
            f"source_provider: {provenance.get('source_provider') or '-'}",
            f"source_framework: {provenance.get('source_framework') or '-'}",
            f"packet_trust_level: {provenance.get('packet_trust_level') or '-'}",
            f"source.file: {source.get('file') or '-'}",
            f"source.symbol: {source.get('symbol') or '-'}",
            f"line_range: {_format_line_range(source)}",
        ]
        for index, line in enumerate(lines):
            label = QLabel(line)
            label.setObjectName(f"truth_label_{index}")
            layout.addWidget(label)

    snapshot = model.serialize_subtree(node.id)
    layout.addWidget(QLabel("Snapshot"))
    snapshot_lines = [
        f"snapshot.root_type: {snapshot.get('type') or '-'}",
        f"snapshot.child_count: {len(snapshot.get('children', []))}",
        f"snapshot.node_count: {_count_snapshot_nodes(snapshot)}",
        f"snapshot.children: {_summarize_snapshot_children(snapshot)}",
    ]
    for index, line in enumerate(snapshot_lines):
        label = QLabel(line)
        label.setObjectName(f"snapshot_label_{index}")
        layout.addWidget(label)

    if resolved["reason"]:
        reason_label = QLabel(f"edit_reason: {resolved['reason']}")
        reason_label.setObjectName("truth_edit_reason")
        layout.addWidget(reason_label)
    if resolved["origin_node_id"]:
        origin_label = QLabel(f"origin_node_id: {resolved['origin_node_id']}")
        origin_label.setObjectName("truth_origin_node_id")
        layout.addWidget(origin_label)
    if resolved["bench_session_id"]:
        bench_label = QLabel(f"bench_session_id: {resolved['bench_session_id']}")
        bench_label.setObjectName("truth_bench_session_id")
        layout.addWidget(bench_label)
    fork_destination = provenance.get("fork_destination")
    if fork_destination:
        destination_label = QLabel(f"fork_destination: {fork_destination}")
        destination_label.setObjectName("truth_fork_destination")
        layout.addWidget(destination_label)
    if resolved["editability"] == "forkable":
        actions = QHBoxLayout()
        fork_button = QPushButton("Fork Here")
        fork_button.setObjectName("truth_fork_to_design")
        fork_button.clicked.connect(
            lambda _checked=False, node_id=node.id: callbacks["fork_selected_to_design"](node_id)
        )
        actions.addWidget(fork_button)
        bench_button = QPushButton("Open In Bench")
        bench_button.setObjectName("truth_open_in_bench")
        bench_button.clicked.connect(
            lambda _checked=False, node_id=node.id: callbacks["open_selected_in_bench"](node_id)
        )
        actions.addWidget(bench_button)
        layout.addLayout(actions)
    elif resolved["resolved_mode"] == "bench" and resolved["bench_session_id"]:
        actions = QHBoxLayout()
        focus_button = QPushButton("Focus Bench Session")
        focus_button.setObjectName("truth_focus_bench_session")
        focus_button.clicked.connect(
            lambda _checked=False, bench_session_id=resolved["bench_session_id"]: callbacks["focus_bench_session"](bench_session_id)
        )
        actions.addWidget(focus_button)
        clear_button = QPushButton("Clear Bench Focus")
        clear_button.setObjectName("truth_clear_bench_focus")
        clear_button.clicked.connect(lambda _checked=False: callbacks["clear_bench_focus"]())
        actions.addWidget(clear_button)
        layout.addLayout(actions)

    if warnings:
        layout.addWidget(QLabel("Warnings"))
        for index, warning in enumerate(warnings):
            label = QLabel(str(warning))
            label.setObjectName(f"truth_warning_{index}")
            layout.addWidget(label)

    relationships = metadata.get("relationships", {})
    if relationships:
        layout.addWidget(QLabel("Relationships"))
        for field_name in ("communicates_to", "depends_on", "updated_by", "triggered_by"):
            values = relationships.get(field_name) or []
            label = QLabel(f"{field_name}: {', '.join(str(value) for value in values) if values else '-'}")
            label.setObjectName(f"truth_relationship_{field_name}")
            layout.addWidget(label)

    unresolved_fields = raw.get("unresolved_fields") or []
    if unresolved_fields:
        layout.addWidget(QLabel("Unresolved Fields"))
        label = QLabel(", ".join(str(field) for field in unresolved_fields))
        label.setObjectName("truth_unresolved_fields")
        layout.addWidget(label)


def build_scene_truth_section(layout, node, model, callbacks):
    scene_metadata = getattr(model, "scene_metadata", {})
    bench_sessions = model.get_bench_session_ids()
    closed_sessions = model.get_recently_closed_bench_session_ids()
    if not (scene_metadata or bench_sessions or closed_sessions):
        return

    scene_resolved = resolve_scene_state(scene_metadata)
    layout.addWidget(QLabel("Scene Truth"))
    scene_lines = [
        f"scene_mode: {scene_resolved['resolved_mode']}",
        f"scene_origin: {scene_resolved['origin']}",
        f"scene_source_provider: {scene_resolved['source_provider']}",
        f"scene_source_framework: {scene_resolved['source_framework']}",
        f"scene_packet_trust_level: {scene_resolved['trust_level']}",
        f"scene_active_bench_session_id: {scene_resolved['active_bench_session_id'] or '-'}",
    ]
    for index, line in enumerate(scene_lines):
        label = QLabel(line)
        label.setObjectName(f"scene_truth_label_{index}")
        layout.addWidget(label)

    if scene_resolved["resolved_mode"] == "source":
        scene_actions = QHBoxLayout()
        fork_scene_button = QPushButton("Fork Scene Here")
        fork_scene_button.setObjectName("scene_truth_fork_scene_here")
        fork_scene_button.clicked.connect(lambda _checked=False: callbacks["fork_scene_to_design"]())
        scene_actions.addWidget(fork_scene_button)
        bench_scene_button = QPushButton("Open Scene In Bench")
        bench_scene_button.setObjectName("scene_truth_open_scene_in_bench")
        bench_scene_button.clicked.connect(lambda _checked=False: callbacks["open_scene_in_bench"]())
        scene_actions.addWidget(bench_scene_button)
        layout.addLayout(scene_actions)

    if bench_sessions:
        layout.addWidget(QLabel("Bench Sessions"))
        for index, bench_session_id in enumerate(bench_sessions):
            row = QHBoxLayout()
            session_label = QLabel(bench_session_id)
            session_label.setObjectName(f"bench_session_label_{index}")
            row.addWidget(session_label)
            focus_button = QPushButton(
                "Active" if bench_session_id == scene_resolved["active_bench_session_id"] else "Focus"
            )
            focus_button.setObjectName(f"bench_session_focus_{index}")
            focus_button.setEnabled(bench_session_id != scene_resolved["active_bench_session_id"])
            focus_button.clicked.connect(
                lambda _checked=False, bench_session_id=bench_session_id: callbacks["focus_bench_session"](bench_session_id)
            )
            row.addWidget(focus_button)
            close_button = QPushButton("Close")
            close_button.setObjectName(f"bench_session_close_{index}")
            close_button.clicked.connect(
                lambda _checked=False, bench_session_id=bench_session_id: callbacks["close_bench_session"](bench_session_id)
            )
            row.addWidget(close_button)
            layout.addLayout(row)
        clear_button = QPushButton("Clear Bench Session Focus")
        clear_button.setObjectName("bench_session_clear_focus")
        clear_button.setEnabled(scene_resolved["active_bench_session_id"] is not None)
        clear_button.clicked.connect(lambda _checked=False: callbacks["clear_bench_focus"]())
        layout.addWidget(clear_button)

    if closed_sessions:
        layout.addWidget(QLabel("Recently Closed Bench Sessions"))
        for index, bench_session_id in enumerate(closed_sessions):
            row = QHBoxLayout()
            session_label = QLabel(bench_session_id)
            session_label.setObjectName(f"closed_bench_session_label_{index}")
            row.addWidget(session_label)
            reopen_button = QPushButton("Reopen")
            reopen_button.setObjectName(f"closed_bench_session_reopen_{index}")
            reopen_button.clicked.connect(
                lambda _checked=False, bench_session_id=bench_session_id: callbacks["reopen_bench_session"](bench_session_id)
            )
            row.addWidget(reopen_button)
            layout.addLayout(row)
