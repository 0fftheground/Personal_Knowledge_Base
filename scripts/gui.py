"""Local desktop GUI for the knowledge workflow.

The GUI is intentionally thin: it reuses the existing storage, triage,
learning, and prompt-generation helpers so the workflow remains state-driven
from the same files as the CLI.
"""

from __future__ import annotations

import os
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

try:  # Optional drag-and-drop support.
    from tkinterdnd2 import DND_FILES, TkinterDnD  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    DND_FILES = None
    TkinterDnD = None

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from tkinter.scrolledtext import ScrolledText

from scripts import agent_workflow
from scripts import ingest_detection
from scripts import learning
from scripts import local_config
from scripts import publish
from scripts import storage
from scripts import triage
from scripts import url_ingest


LOGGER = logging.getLogger(__name__)
APP_TITLE = "PKLS Local Workflow"
AUTO_REFRESH_MS = 10_000


class KnowledgeWorkflowApp((TkinterDnD.Tk if TkinterDnD is not None else tk.Tk)):
    """Desktop controller for add / triage / learning / config tasks."""

    def __init__(self, root_dir: Path | None = None) -> None:
        super().__init__()
        self.repo_root = root_dir or storage.get_repo_root()
        self.workspace_root: Path | None = None
        self._drop_enabled = DND_FILES is not None

        self.title(APP_TITLE)
        self.geometry("1360x900")
        self.minsize(1180, 760)

        self._configure_style()

        self.status_var = tk.StringVar(value="Ready")
        self.config_summary_var = tk.StringVar()
        self.dashboard_summary_var = tk.StringVar(value="Loading...")
        self.add_hint_var = tk.StringVar()
        self.triage_detail_var = tk.StringVar()
        self.learning_detail_var = tk.StringVar()

        self.ingest_source_var = tk.StringVar(value="manual")
        self.ingest_content_type_var = tk.StringVar(value="blog")
        self.ingest_storage_mode_var = tk.StringVar(value="library")
        self.ingest_accept_var = tk.BooleanVar(value=False)
        self.ingest_title_var = tk.StringVar()
        self.learning_focus_var = tk.StringVar()
        self.triage_filter_var = tk.StringVar()
        self.learning_filter_var = tk.StringVar()
        self.triage_latest_prompt_var = tk.StringVar(value="Latest triage prompt: none")
        self.learning_latest_prompt_var = tk.StringVar(value="Latest learning prompt: none")

        self.device_name_var = tk.StringVar()
        self.raw_full_root_var = tk.StringVar()
        self.raw_sync_root_var = tk.StringVar()
        self.workspace_root_var = tk.StringVar()
        self.obsidian_vault_var = tk.StringVar()

        self.ingest_paths: list[Path] = []
        self.triage_rows: list[dict[str, Any]] = []
        self.learning_rows: list[dict[str, Any]] = []
        self.attention_rows: list[dict[str, Any]] = []
        self.recent_operations: list[str] = []
        self._triage_selection_buttons: list[ttk.Button] = []
        self._learning_selection_buttons: list[ttk.Button] = []

        self._build_ui()
        self.triage_filter_var.trace_add("write", lambda *_: self._refresh_triage_tab())
        self.learning_filter_var.trace_add("write", lambda *_: self._refresh_learning_tab())
        self._load_config_fields()
        self._refresh_all()
        self.after(AUTO_REFRESH_MS, self._auto_refresh)

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("App.TLabel", padding=(4, 2))
        style.configure("Section.TLabelframe", padding=10)
        style.configure("Section.TLabelframe.Label", font=("TkDefaultFont", 10, "bold"))

    def _build_ui(self) -> None:
        container = ttk.Frame(self, padding=12)
        container.pack(fill="both", expand=True)

        header = ttk.Frame(container)
        header.pack(fill="x")

        ttk.Label(header, text=APP_TITLE, font=("TkDefaultFont", 18, "bold")).pack(anchor="w")
        ttk.Label(
            header,
            text="A local desktop control panel for add, triage, learning, and consolidation.",
        ).pack(anchor="w", pady=(4, 0))

        summary_bar = ttk.Frame(container)
        summary_bar.pack(fill="x", pady=(10, 8))
        ttk.Label(summary_bar, textvariable=self.config_summary_var, style="App.TLabel").pack(anchor="w")
        ttk.Label(summary_bar, textvariable=self.dashboard_summary_var, style="App.TLabel").pack(anchor="w")
        ttk.Label(summary_bar, textvariable=self.status_var, style="App.TLabel").pack(anchor="w")

        self.notebook = ttk.Notebook(container)
        self.notebook.pack(fill="both", expand=True)

        self.dashboard_tab = ttk.Frame(self.notebook, padding=12)
        self.add_tab = ttk.Frame(self.notebook, padding=12)
        self.triage_tab = ttk.Frame(self.notebook, padding=12)
        self.learning_tab = ttk.Frame(self.notebook, padding=12)
        self.config_tab = ttk.Frame(self.notebook, padding=12)

        self.notebook.add(self.dashboard_tab, text="Dashboard")
        self.notebook.add(self.add_tab, text="Add New Content")
        self.notebook.add(self.triage_tab, text="Triage")
        self.notebook.add(self.learning_tab, text="Learning")
        self.notebook.add(self.config_tab, text="Config")

        self._build_dashboard_tab()
        self._build_add_tab()
        self._build_triage_tab()
        self._build_learning_tab()
        self._build_config_tab()
        self._build_log_panel(container)

    def _build_dashboard_tab(self) -> None:
        summary_box = ttk.Labelframe(self.dashboard_tab, text="Workspace Snapshot", style="Section.TLabelframe")
        summary_box.pack(fill="x")
        self.dashboard_counts_text = ScrolledText(summary_box, height=10, wrap="word")
        self.dashboard_counts_text.pack(fill="x", expand=False)
        self.dashboard_counts_text.configure(state="disabled")

        recent_box = ttk.Labelframe(self.dashboard_tab, text="Recent Operations", style="Section.TLabelframe")
        recent_box.pack(fill="x", pady=(10, 0))
        self.recent_operations_text = ScrolledText(recent_box, height=6, wrap="word")
        self.recent_operations_text.pack(fill="x", expand=False)
        self.recent_operations_text.configure(state="disabled")
        self._refresh_recent_operations_panel()

        actions = ttk.Frame(self.dashboard_tab)
        actions.pack(fill="x", pady=(10, 0))
        ttk.Button(actions, text="Refresh All", command=self.refresh_all).pack(side="left")
        ttk.Button(actions, text="Go To Add", command=lambda: self.notebook.select(self.add_tab)).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Go To Triage", command=lambda: self.notebook.select(self.triage_tab)).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Go To Learning", command=lambda: self.notebook.select(self.learning_tab)).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Go To Config", command=lambda: self.notebook.select(self.config_tab)).pack(side="left", padx=(8, 0))

        attention_box = ttk.Labelframe(self.dashboard_tab, text="Attention Queue", style="Section.TLabelframe")
        attention_box.pack(fill="both", expand=True, pady=(12, 0))
        self.dashboard_attention_tree = self._build_tree(
            attention_box,
            columns=("domain", "id", "title", "state", "next_action"),
            headings={
                "domain": "Area",
                "id": "ID",
                "title": "Title",
                "state": "State",
                "next_action": "Next Action",
            },
            widths={"domain": 80, "id": 180, "title": 260, "state": 100, "next_action": 360},
        )
        self.dashboard_attention_tree.bind("<<TreeviewSelect>>", self._on_dashboard_select)
        self.dashboard_attention_tree.bind("<Double-1>", self._open_dashboard_selection)

        dash_actions = ttk.Frame(self.dashboard_tab)
        dash_actions.pack(fill="x", pady=(10, 0))
        ttk.Button(dash_actions, text="Open Selected", command=self._open_dashboard_selection).pack(side="left")
        ttk.Button(dash_actions, text="Generate Selected Prompt", command=self._generate_dashboard_prompt).pack(side="left", padx=(8, 0))
        ttk.Button(dash_actions, text="Open Log", command=lambda: self.log_text.focus_set()).pack(side="left", padx=(8, 0))

    def _build_add_tab(self) -> None:
        controls = ttk.Labelframe(self.add_tab, text="Add Content", style="Section.TLabelframe")
        controls.pack(fill="x")

        row1 = ttk.Frame(controls)
        row1.pack(fill="x", pady=(0, 6))
        ttk.Label(row1, text="Source type").pack(side="left")
        ttk.Combobox(
            row1,
            textvariable=self.ingest_source_var,
            values=sorted(storage.SOURCE_TYPES),
            width=12,
            state="readonly",
        ).pack(side="left", padx=(8, 16))
        ttk.Label(row1, text="Content type").pack(side="left")
        ttk.Combobox(
            row1,
            textvariable=self.ingest_content_type_var,
            values=sorted(storage.CONTENT_TYPES),
            width=12,
            state="readonly",
        ).pack(side="left", padx=(8, 16))
        ttk.Label(row1, text="Storage mode").pack(side="left")
        ttk.Combobox(
            row1,
            textvariable=self.ingest_storage_mode_var,
            values=["library", "inbox"],
            width=12,
            state="readonly",
        ).pack(side="left", padx=(8, 16))
        ttk.Checkbutton(row1, text="Accept on ingest", variable=self.ingest_accept_var).pack(side="left")

        ttk.Label(
            controls,
            text="library mode uses .pkls.local.json to decide whether raw files land in full and/or sync storage; inbox mode writes to raw_sync_root/inbox/<device_name>/",
            justify="left",
        ).pack(anchor="w", pady=(0, 6))

        row2 = ttk.Frame(controls)
        row2.pack(fill="x", pady=(0, 6))
        ttk.Label(row2, text="Title override").pack(side="left")
        ttk.Entry(row2, textvariable=self.ingest_title_var, width=60).pack(side="left", padx=(8, 16), fill="x", expand=True)
        ttk.Button(row2, text="Choose Files", command=self._choose_ingest_files).pack(side="left")
        ttk.Button(row2, text="Clear", command=self._clear_ingest_paths).pack(side="left", padx=(8, 0))

        drop_box = ttk.Labelframe(self.add_tab, text="Drop Zone", style="Section.TLabelframe")
        drop_box.pack(fill="x", pady=(12, 0))
        self.drop_label = ttk.Label(
            drop_box,
            text=self._drop_zone_text(),
            anchor="center",
            justify="center",
        )
        self.drop_label.pack(fill="x", pady=12)
        self._register_drop_target(drop_box)
        self._register_drop_target(self.drop_label)

        list_box = ttk.Labelframe(self.add_tab, text="Queued Files", style="Section.TLabelframe")
        list_box.pack(fill="both", expand=True, pady=(12, 0))
        list_frame = ttk.Frame(list_box)
        list_frame.pack(fill="both", expand=True)
        self.ingest_list = tk.Listbox(list_frame, height=8, selectmode="extended")
        ingest_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.ingest_list.yview)
        self.ingest_list.configure(yscrollcommand=ingest_scroll.set)
        self.ingest_list.pack(side="left", fill="both", expand=True)
        ingest_scroll.pack(side="right", fill="y")
        self._register_drop_target(list_frame)
        self._register_drop_target(self.ingest_list)
        self._register_drop_target(ingest_scroll)

        buttons = ttk.Frame(self.add_tab)
        buttons.pack(fill="x", pady=(10, 0))
        ttk.Button(buttons, text="Run Ingest", command=self._add_selected_files).pack(side="left")
        ttk.Button(buttons, text="Remove Selected", command=self._remove_selected_ingest_paths).pack(side="left", padx=(8, 0))
        ttk.Label(buttons, textvariable=self.add_hint_var).pack(side="left", padx=(12, 0))

    def _build_triage_tab(self) -> None:
        top = ttk.Frame(self.triage_tab)
        top.pack(fill="both", expand=True)

        _paned, left, right = self._build_horizontal_split(top, initial_ratio=0.38)

        filter_row = ttk.Frame(left)
        filter_row.pack(fill="x", pady=(0, 8))
        ttk.Label(filter_row, text="Filter").pack(side="left")
        ttk.Entry(filter_row, textvariable=self.triage_filter_var).pack(side="left", fill="x", expand=True, padx=(8, 0))
        ttk.Button(filter_row, text="Clear", command=lambda: self.triage_filter_var.set("")).pack(side="left", padx=(8, 0))

        tree_box = ttk.Labelframe(left, text="Candidate Items", style="Section.TLabelframe")
        tree_box.pack(fill="both", expand=True)
        self.triage_tree = self._build_tree(
            tree_box,
            columns=("id", "title", "priority", "recommendation", "decision", "next_action"),
            headings={
                "id": "ID",
                "title": "Title",
                "priority": "Priority",
                "recommendation": "Recommendation",
                "decision": "Decision",
                "next_action": "Next Action",
            },
            widths={"id": 180, "title": 240, "priority": 70, "recommendation": 120, "decision": 90, "next_action": 260},
        )
        self.triage_tree.bind("<<TreeviewSelect>>", self._on_triage_select)

        actions = ttk.Frame(left)
        actions.pack(fill="x", pady=(10, 0))
        self.triage_generate_button = ttk.Button(actions, text="Generate Prompt", command=self._generate_triage_prompt)
        self.triage_generate_button.pack(side="left")
        ttk.Button(actions, text="Generate Batch Prompt", command=self._generate_triage_batch_prompt).pack(side="left", padx=(8, 0))
        self.triage_accept_button = ttk.Button(actions, text="Accept", command=lambda: self._triage_decision("accept"))
        self.triage_accept_button.pack(side="left", padx=(8, 0))
        self.triage_reject_button = ttk.Button(actions, text="Reject", command=lambda: self._triage_decision("reject"))
        self.triage_reject_button.pack(side="left", padx=(8, 0))
        self.triage_later_button = ttk.Button(actions, text="Later", command=lambda: self._triage_decision("later"))
        self.triage_later_button.pack(side="left", padx=(8, 0))
        self.triage_publish_button = ttk.Button(actions, text="Publish Card", command=self._publish_triage_card)
        self.triage_publish_button.pack(side="left", padx=(8, 0))
        self._triage_selection_buttons = [
            self.triage_generate_button,
            self.triage_accept_button,
            self.triage_reject_button,
            self.triage_later_button,
            self.triage_publish_button,
        ]

        detail_box = ttk.Labelframe(right, text="Selected Item", style="Section.TLabelframe")
        detail_box.pack(fill="both", expand=True)
        detail_actions = ttk.Frame(detail_box)
        detail_actions.pack(fill="x", pady=(0, 6))
        self.triage_raw_button = ttk.Button(detail_actions, text="Open Raw", command=self._open_selected_triage_raw)
        self.triage_raw_button.pack(side="left")
        self.triage_metadata_button = ttk.Button(detail_actions, text="Open Metadata", command=self._open_selected_triage_metadata)
        self.triage_metadata_button.pack(side="left", padx=(8, 0))
        self.triage_card_button = ttk.Button(detail_actions, text="Open Card", command=self._open_selected_triage_card)
        self.triage_card_button.pack(side="left", padx=(8, 0))
        self.triage_prompt_button = ttk.Button(detail_actions, text="Open Prompt", command=self._open_selected_triage_prompt)
        self.triage_prompt_button.pack(side="left", padx=(8, 0))
        self.triage_copy_paths_button = ttk.Button(detail_actions, text="Copy Paths", command=self._copy_selected_triage_paths)
        self.triage_copy_paths_button.pack(side="left", padx=(8, 0))
        self._triage_selection_buttons.extend(
            [
                self.triage_raw_button,
                self.triage_metadata_button,
                self.triage_card_button,
                self.triage_prompt_button,
                self.triage_copy_paths_button,
            ]
        )
        ttk.Label(detail_box, textvariable=self.triage_latest_prompt_var, justify="left", wraplength=620).pack(anchor="w", pady=(0, 6))
        self.triage_detail = ScrolledText(detail_box, wrap="word", height=24)
        self.triage_detail.pack(fill="both", expand=True)
        self.triage_detail.configure(state="disabled")
        self._set_triage_buttons_enabled(False)

    def _build_learning_tab(self) -> None:
        top = ttk.Frame(self.learning_tab)
        top.pack(fill="both", expand=True)

        _paned, left, right = self._build_horizontal_split(top, initial_ratio=0.36)

        filter_row = ttk.Frame(left)
        filter_row.pack(fill="x", pady=(0, 8))
        ttk.Label(filter_row, text="Filter").pack(side="left")
        ttk.Entry(filter_row, textvariable=self.learning_filter_var).pack(side="left", fill="x", expand=True, padx=(8, 0))
        ttk.Button(filter_row, text="Clear", command=lambda: self.learning_filter_var.set("")).pack(side="left", padx=(8, 0))

        tree_box = ttk.Labelframe(left, text="Learning Queue", style="Section.TLabelframe")
        tree_box.pack(fill="both", expand=True)
        self.learning_tree = self._build_tree(
            tree_box,
            columns=("id", "title", "status", "queue", "progress", "mode", "next_action"),
            headings={
                "id": "ID",
                "title": "Title",
                "status": "Status",
                "queue": "Queue",
                "progress": "Progress",
                "mode": "Mode",
                "next_action": "Next Action",
            },
            widths={"id": 180, "title": 220, "status": 90, "queue": 80, "progress": 80, "mode": 90, "next_action": 260},
        )
        self.learning_tree.bind("<<TreeviewSelect>>", self._on_learning_select)

        focus_row = ttk.Frame(left)
        focus_row.pack(fill="x", pady=(10, 0))
        ttk.Label(focus_row, text="Focus").pack(side="left")
        ttk.Entry(focus_row, textvariable=self.learning_focus_var).pack(side="left", fill="x", expand=True, padx=(8, 0))

        actions = ttk.Frame(left)
        actions.pack(fill="x", pady=(10, 0))
        self.learning_generate_button = ttk.Button(actions, text="Generate Learning Prompt", command=self._generate_learning_prompt)
        self.learning_generate_button.pack(side="left")
        ttk.Button(actions, text="Next Queue Prompt", command=self._generate_next_learning_prompt).pack(side="left", padx=(8, 0))
        self.learning_pause_button = ttk.Button(actions, text="Pause Prompt", command=self._generate_pause_prompt)
        self.learning_pause_button.pack(side="left", padx=(8, 0))
        self.learning_consolidate_button = ttk.Button(actions, text="Consolidate Prompt", command=self._generate_consolidate_prompt)
        self.learning_consolidate_button.pack(side="left", padx=(8, 0))
        self.learning_publish_button = ttk.Button(actions, text="Publish Outputs", command=self._publish_learning_outputs)
        self.learning_publish_button.pack(side="left", padx=(8, 0))
        self._learning_selection_buttons = [
            self.learning_generate_button,
            self.learning_pause_button,
            self.learning_consolidate_button,
            self.learning_publish_button,
        ]

        detail_box = ttk.Labelframe(right, text="Selected Item", style="Section.TLabelframe")
        detail_box.pack(fill="both", expand=True)
        ttk.Label(detail_box, textvariable=self.learning_latest_prompt_var, justify="left", wraplength=620).pack(anchor="w", pady=(0, 6))
        detail_actions = ttk.Frame(detail_box)
        detail_actions.pack(fill="x", pady=(0, 6))
        self.learning_raw_button = ttk.Button(detail_actions, text="Open Raw", command=self._open_selected_learning_raw)
        self.learning_raw_button.pack(side="left")
        self.learning_metadata_button = ttk.Button(detail_actions, text="Open Metadata", command=self._open_selected_learning_metadata)
        self.learning_metadata_button.pack(side="left", padx=(8, 0))
        self.learning_state_button = ttk.Button(detail_actions, text="Open State", command=self._open_selected_learning_state)
        self.learning_state_button.pack(side="left", padx=(8, 0))
        self.learning_outline_button = ttk.Button(detail_actions, text="Open Outline", command=self._open_selected_learning_outline)
        self.learning_outline_button.pack(side="left", padx=(8, 0))
        self.learning_outputs_button = ttk.Button(detail_actions, text="Open Outputs", command=self._open_selected_learning_outputs)
        self.learning_outputs_button.pack(side="left", padx=(8, 0))
        self.learning_prompt_dir_button = ttk.Button(detail_actions, text="Open Prompt Dir", command=self._open_learning_prompt_dir)
        self.learning_prompt_dir_button.pack(side="left", padx=(8, 0))
        self.learning_copy_paths_button = ttk.Button(detail_actions, text="Copy Paths", command=self._copy_selected_learning_paths)
        self.learning_copy_paths_button.pack(side="left", padx=(8, 0))
        self._learning_selection_buttons.extend(
            [
                self.learning_raw_button,
                self.learning_metadata_button,
                self.learning_state_button,
                self.learning_outline_button,
                self.learning_outputs_button,
                self.learning_copy_paths_button,
            ]
        )
        self.learning_detail = ScrolledText(detail_box, wrap="word", height=24)
        self.learning_detail.pack(fill="both", expand=True)
        self.learning_detail.configure(state="disabled")
        self._set_learning_buttons_enabled(False)

    def _build_config_tab(self) -> None:
        info = ttk.Labelframe(self.config_tab, text="Local Config", style="Section.TLabelframe")
        info.pack(fill="x")
        ttk.Label(info, text=f"Config file: {local_config.get_local_config_path(self.repo_root)}").pack(anchor="w")

        grid = ttk.Frame(self.config_tab)
        grid.pack(fill="both", expand=True, pady=(12, 0))

        self._build_config_row(grid, 0, "Device name", self.device_name_var, "text", self._set_device_name)
        self._build_config_row(grid, 1, "Raw full root", self.raw_full_root_var, "dir", self._set_raw_full_root)
        self._build_config_row(grid, 2, "Raw sync root", self.raw_sync_root_var, "dir", self._set_raw_sync_root)
        self._build_config_row(grid, 3, "Workspace root", self.workspace_root_var, "dir", self._set_workspace_root)
        self._build_config_row(grid, 4, "Obsidian vault", self.obsidian_vault_var, "dir", self._set_obsidian_vault)

        hint = ttk.Labelframe(self.config_tab, text="Notes", style="Section.TLabelframe")
        hint.pack(fill="x", pady=(12, 0))
        ttk.Label(
            hint,
            text=(
                "Set workspace_root first if you want the GUI to create the workspace layout.\n"
                "The add / triage / learning tabs become fully usable once workspace_root and the raw roots are configured."
            ),
            justify="left",
        ).pack(anchor="w")

    def _build_config_row(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        variable: tk.StringVar,
        mode: str,
        setter: Callable[[], None],
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=6)
        entry = ttk.Entry(parent, textvariable=variable, width=80)
        entry.grid(row=row, column=1, sticky="ew", pady=6)
        if mode == "dir":
            ttk.Button(parent, text="Browse", command=lambda: self._browse_directory(variable)).grid(row=row, column=2, padx=(8, 0), pady=6)
        ttk.Button(parent, text="Set", command=setter).grid(row=row, column=3, padx=(8, 0), pady=6)
        parent.grid_columnconfigure(1, weight=1)

    def _build_log_panel(self, parent: ttk.Frame) -> None:
        log_box = ttk.Labelframe(parent, text="Activity Log", style="Section.TLabelframe")
        log_box.pack(fill="both", expand=False, pady=(12, 0))
        self.log_text = ScrolledText(log_box, height=9, wrap="word")
        self.log_text.pack(fill="both", expand=True)
        self.log_text.configure(state="disabled")

    def _build_tree(
        self,
        parent: ttk.Frame,
        *,
        columns: tuple[str, ...],
        headings: dict[str, str],
        widths: dict[str, int],
    ) -> ttk.Treeview:
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True)
        tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="browse")
        yscroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        xscroll = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        for column in columns:
            tree.heading(column, text=headings[column])
            tree.column(column, width=widths.get(column, 120), anchor="w", stretch=True)
        return tree

    def _build_horizontal_split(
        self,
        parent: ttk.Frame,
        *,
        initial_ratio: float,
    ) -> tuple[ttk.Panedwindow, ttk.Frame, ttk.Frame]:
        paned = ttk.Panedwindow(parent, orient="horizontal")
        paned.pack(fill="both", expand=True)
        left = ttk.Frame(paned)
        right = ttk.Frame(paned)
        paned.add(left, weight=1)
        paned.add(right, weight=2)
        self.after_idle(lambda p=paned, ratio=initial_ratio: self._set_paned_ratio(p, ratio))
        return paned, left, right

    def _set_paned_ratio(self, paned: ttk.Panedwindow, ratio: float) -> None:
        try:
            total_width = paned.winfo_width()
            if total_width <= 1:
                self.after(100, lambda: self._set_paned_ratio(paned, ratio))
                return
            sash_position = max(320, int(total_width * ratio))
            paned.sashpos(0, sash_position)
        except Exception:
            LOGGER.debug("Unable to set paned ratio", exc_info=True)

    def run(self) -> None:
        self.mainloop()

    def refresh_all(self) -> None:
        self._load_config_fields()
        self._refresh_config_tab()
        self._refresh_dashboard()
        self._refresh_lists()
        self._set_status("Refreshed")

    def _refresh_lists(self) -> None:
        self._refresh_triage_tab()
        self._refresh_learning_tab()

    def _refresh_dashboard(self) -> None:
        text = self._build_dashboard_text()
        self._set_text(self.dashboard_counts_text, text)
        self._refresh_dashboard_attention()
        self.dashboard_summary_var.set(self._build_dashboard_summary())

    def _refresh_config_tab(self) -> None:
        self._load_config_fields()
        self.config_summary_var.set(self._build_config_summary())
        self._update_config_status()

    def _refresh_triage_tab(self) -> None:
        previous_selection = self._current_tree_selection(self.triage_tree) if hasattr(self, "triage_tree") else None
        self._clear_tree(self.triage_tree)
        self.triage_rows = []
        workspace_root = self._require_workspace_root(optional=True)
        if workspace_root is None:
            self._set_text(
                self.triage_detail,
                "workspace_root is not configured yet. Open the Config tab first.",
            )
            self._set_status("Workspace not configured")
            self._set_triage_buttons_enabled(False)
            return

        try:
            rows = triage.list_candidate_reviews(self.repo_root)
            self.triage_rows = self._filter_triage_rows(rows, self.triage_filter_var.get().strip())
        except Exception as exc:
            self._show_error("Failed to load triage items", exc)
            self._set_text(self.triage_detail, str(exc))
            self._set_triage_buttons_enabled(False)
            return

        for row in self.triage_rows:
            item = row["item"]
            triage_card = row["triage_card"]
            recommendation = item["ai_recommendation"]
            summary = ""
            reason = ""
            if triage_card is not None:
                recommendation = triage_card.get("recommendation") or recommendation
                summary = triage_card.get("summary") or ""
                reason = triage_card.get("reason") or ""
            self.triage_tree.insert(
                "",
                "end",
                iid=item["id"],
                values=(
                    item["id"],
                    item["title"],
                    f"{item['priority']:.2f}",
                    recommendation,
                    item["manual_decision"] or "",
                    self._preview_text(summary or reason or "Needs prompt"),
                ),
            )

        self._set_triage_buttons_enabled(True)
        self._restore_tree_selection(
            self.triage_tree,
            [row["item"]["id"] for row in self.triage_rows],
            previous_selection,
            self._show_triage_details,
            "Select a candidate to inspect its metadata and triage card.",
        )
        self._set_status(f"Loaded {len(self.triage_rows)} triage candidates")

    def _refresh_learning_tab(self) -> None:
        previous_selection = self._current_tree_selection(self.learning_tree) if hasattr(self, "learning_tree") else None
        self._clear_tree(self.learning_tree)
        self.learning_rows = []
        workspace_root = self._require_workspace_root(optional=True)
        if workspace_root is None:
            self._set_text(
                self.learning_detail,
                "workspace_root is not configured yet. Open the Config tab first.",
            )
            self._set_learning_buttons_enabled(False)
            return

        try:
            rows = learning.list_learning_items(self.repo_root)
            self.learning_rows = self._filter_learning_rows(rows, self.learning_filter_var.get().strip())
        except Exception as exc:
            self._show_error("Failed to load learning items", exc)
            self._set_text(self.learning_detail, str(exc))
            self._set_learning_buttons_enabled(False)
            return

        for row in self.learning_rows:
            item = row["item"]
            queue_entry = row["queue_entry"]
            state = row["state"]
            progress = "n/a" if state is None else f"{float(state['progress']) * 100:.0f}%"
            mode = "n/a" if state is None else state["processing_mode"]
            queue_status = "none" if queue_entry is None else queue_entry["status"]
            self.learning_tree.insert(
                "",
                "end",
                iid=item["id"],
                values=(
                    item["id"],
                    item["title"],
                    item["status"],
                    queue_status,
                    progress,
                    mode,
                    self._preview_text(row["next_action"]),
                ),
            )

        self._set_learning_buttons_enabled(True)
        self._restore_tree_selection(
            self.learning_tree,
            [row["item"]["id"] for row in self.learning_rows],
            previous_selection,
            self._show_learning_details,
            "Select a learning item to inspect its state and outputs.",
        )
        self._set_status(f"Loaded {len(self.learning_rows)} learning items")

    def _load_config_fields(self) -> None:
        config = local_config.read_local_config(self.repo_root)
        self.device_name_var.set(str(config.get("device_name", "") or ""))
        self.raw_full_root_var.set(str(config.get("raw_full_root", "") or ""))
        self.raw_sync_root_var.set(str(config.get("raw_sync_root", "") or ""))
        self.workspace_root_var.set(str(config.get("workspace_root", "") or ""))
        self.obsidian_vault_var.set(str(config.get("obsidian_vault_path", "") or ""))
        self.workspace_root = local_config.get_workspace_root(self.repo_root)
        if self.workspace_root is not None:
            storage.ensure_storage_layout(self.repo_root)

    def _build_dashboard_text(self) -> str:
        try:
            counts = self._collect_counts()
        except Exception as exc:
            return f"Unable to collect dashboard stats yet:\n{exc}"

        workspace = self.workspace_root or local_config.get_workspace_root(self.repo_root)
        raw_full = local_config.get_raw_full_root(self.repo_root)
        raw_sync = local_config.get_raw_sync_root(self.repo_root)
        vault = local_config.get_obsidian_vault_path(self.repo_root)

        lines = [
            "Workspace Overview",
            f"- workspace_root: {workspace if workspace is not None else 'not set'}",
            f"- raw_full_root: {raw_full if raw_full is not None else 'not set'}",
            f"- raw_sync_root: {raw_sync if raw_sync is not None else 'not set'}",
            f"- obsidian_vault_path: {vault if vault is not None else 'not set'}",
            "",
            "Content Counts",
            f"- candidate: {counts['candidate']}",
            f"- accepted: {counts['accepted']}",
            f"- rejected: {counts['rejected']}",
            f"- learning: {counts['learning']}",
            f"- paused: {counts['paused']}",
            f"- done: {counts['done']}",
            f"- archived: {counts['archived']}",
            "",
            "Workflow Counts",
            f"- triage cards ready: {counts['triage_ready']}",
            f"- triage cards pending: {counts['triage_pending']}",
            f"- learning queue entries: {counts['learning_queue']}",
            f"- items ready to consolidate: {counts['ready_to_consolidate']}",
        ]
        return "\n".join(lines)

    def _build_dashboard_summary(self) -> str:
        try:
            counts = self._collect_counts()
        except Exception as exc:
            return f"Dashboard unavailable: {exc}"
        return (
            "Ready"
            f" | candidates={counts['candidate']}"
            f" | accepted={counts['accepted']}"
            f" | learning={counts['learning']}"
            f" | paused={counts['paused']}"
            f" | done={counts['done']}"
        )

    def _build_config_summary(self) -> str:
        pieces = [
            f"device={self.device_name_var.get() or 'not set'}",
            f"workspace={self.workspace_root_var.get() or 'not set'}",
            f"raw_sync={self.raw_sync_root_var.get() or 'not set'}",
            f"raw_full={self.raw_full_root_var.get() or 'not set'}",
            f"vault={self.obsidian_vault_var.get() or 'not set'}",
        ]
        return "Config | " + " | ".join(pieces)

    def _update_config_status(self) -> None:
        workspace_ready = self._workspace_ready()
        if workspace_ready:
            self._set_status("Workspace configured")
        else:
            self._set_status("Workspace not configured")

    def _collect_counts(self) -> dict[str, int]:
        self._require_workspace_root()
        items = storage.list_content_items(self.repo_root)
        counts = {status: 0 for status in storage.CONTENT_STATUSES}
        for item in items:
            counts[item["status"]] += 1

        triage_rows = triage.list_candidate_reviews(self.repo_root)
        learning_rows = learning.sync_queue(self.repo_root)
        ready_to_consolidate = 0
        for item in items:
            if item["status"] in {"learning", "paused", "done"} and storage.learning_state_exists(item["id"], self.repo_root):
                state = storage.read_learning_state(item["id"], self.repo_root)
                if state["ready_to_consolidate"]:
                    ready_to_consolidate += 1

        return {
            "candidate": counts["candidate"],
            "accepted": counts["accepted"],
            "rejected": counts["rejected"],
            "learning": counts["learning"],
            "paused": counts["paused"],
            "done": counts["done"],
            "archived": counts["archived"],
            "triage_ready": sum(1 for row in triage_rows if row["triage_card"] is not None),
            "triage_pending": sum(1 for row in triage_rows if row["triage_card"] is None),
            "learning_queue": len(learning_rows),
            "ready_to_consolidate": ready_to_consolidate,
        }

    def _refresh_dashboard_attention(self) -> None:
        self._clear_tree(self.dashboard_attention_tree)
        try:
            triage_rows = triage.list_candidate_reviews(self.repo_root)
            learning_rows = learning.list_learning_items(self.repo_root)
        except Exception as exc:
            self._set_text(self.dashboard_counts_text, f"{self._build_dashboard_text()}\n\nAttention queue unavailable:\n{exc}")
            return

        attention_rows: list[dict[str, Any]] = []

        for row in triage_rows[:8]:
            item = row["item"]
            triage_card = row["triage_card"]
            next_action = "Generate triage prompt" if triage_card is None else "Review triage card and decide"
            attention_rows.append(
                {
                    "domain": "triage",
                    "id": item["id"],
                    "title": item["title"],
                    "state": item["status"],
                    "next_action": next_action,
                }
            )

        for row in learning_rows[:8]:
            item = row["item"]
            queue_entry = row["queue_entry"]
            state = row["state"]
            state_label = "not started" if state is None else f"{state['status']} / {state['processing_mode']}"
            next_action = row["next_action"]
            if queue_entry is not None:
                state_label = f"queue:{queue_entry['status']} | {state_label}"
            attention_rows.append(
                {
                    "domain": "learn",
                    "id": item["id"],
                    "title": item["title"],
                    "state": state_label,
                    "next_action": next_action,
                }
            )

        self.attention_rows = attention_rows
        for row in attention_rows:
            self.dashboard_attention_tree.insert(
                "",
                "end",
                iid=f"{row['domain']}::{row['id']}",
                values=(row["domain"], row["id"], row["title"], row["state"], self._preview_text(row["next_action"], 140)),
            )

    def _on_triage_select(self, _: tk.Event) -> None:
        doc_id = self._selected_tree_id(self.triage_tree)
        if doc_id is None:
            self._set_triage_buttons_enabled(False)
            return
        self._show_triage_details(doc_id)
        self._set_triage_buttons_enabled(True)

    def _show_triage_details(self, doc_id: str) -> None:
        try:
            item = storage.read_content_item_by_id(doc_id, self.repo_root)
            card = triage.read_triage_card(doc_id, self.repo_root)
            raw_path = storage.resolve_raw_path(item, self.repo_root)
            metadata_path = storage.get_content_item_path(item["source_type"], item["id"], self.repo_root)
            card_path = storage.get_triage_cards_root(self.repo_root) / f"{doc_id}.md"
            prompt_path = storage.get_triage_prompts_root(self.repo_root) / f"{doc_id}.md"
            raw_preview = self._raw_preview(item)
            latest_prompt_path = self._latest_triage_prompt_path(doc_id)
        except Exception as exc:
            self._show_error("Unable to load triage detail", exc)
            return

        if latest_prompt_path is None:
            self.triage_latest_prompt_var.set("Latest triage prompt: none")
        else:
            self.triage_latest_prompt_var.set(f"Latest triage prompt: {latest_prompt_path}")

        lines = [
            f"ID: {item['id']}",
            f"Title: {item['title']}",
            f"Status: {item['status']}",
            f"Manual decision: {item['manual_decision']}",
            f"AI recommendation: {item['ai_recommendation']}",
            f"Priority: {item['priority']}",
            f"Storage tier: {item['storage_tier']}",
            f"Raw path: {raw_path}",
            f"Metadata path: {metadata_path}",
            f"Triage card path: {card_path}",
            f"Triage prompt path: {prompt_path}",
            "",
            "Raw preview:",
            raw_preview,
            "",
            "Card:",
            self._format_triage_card(card),
        ]
        self._set_text(self.triage_detail, "\n".join(lines))

    def _on_learning_select(self, _: tk.Event) -> None:
        doc_id = self._selected_tree_id(self.learning_tree)
        if doc_id is None:
            self._set_learning_buttons_enabled(False)
            return
        self._show_learning_details(doc_id)
        self._set_learning_buttons_enabled(True)

    def _on_dashboard_select(self, _: tk.Event) -> None:
        selection = self.dashboard_attention_tree.selection()
        if not selection:
            return
        domain, doc_id = self._split_dashboard_iid(selection[0])
        if domain == "triage":
            self._show_triage_details(doc_id)
        else:
            self._show_learning_details(doc_id)

    def _open_dashboard_selection(self, event: tk.Event | None = None) -> None:
        del event
        selection = self.dashboard_attention_tree.selection()
        if not selection:
            messagebox.showinfo("Selection Required", "Select an attention item first.")
            return
        domain, doc_id = self._split_dashboard_iid(selection[0])
        if domain == "triage":
            self.notebook.select(self.triage_tab)
            self._select_tree_item(self.triage_tree, doc_id)
            self._show_triage_details(doc_id)
            self._set_triage_buttons_enabled(True)
        else:
            self.notebook.select(self.learning_tab)
            self._select_tree_item(self.learning_tree, doc_id)
            self._show_learning_details(doc_id)
            self._set_learning_buttons_enabled(True)

    def _generate_dashboard_prompt(self) -> None:
        selection = self.dashboard_attention_tree.selection()
        if not selection:
            messagebox.showinfo("Selection Required", "Select an attention item first.")
            return
        domain, doc_id = self._split_dashboard_iid(selection[0])
        if domain == "triage":
            self._run_action(
                f"Generate triage prompt for {doc_id}",
                lambda: self._generate_triage_prompt_action(doc_id),
            )
            return
        mode = learning.resolve_learning_mode(doc_id, self.repo_root)
        focus = self.learning_focus_var.get().strip() or None
        self._run_action(
            f"Generate learning prompt for {doc_id}",
            lambda: self._generate_learning_prompt_action(doc_id, mode, focus),
        )

    def _filter_triage_rows(self, rows: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
        normalized_query = query.lower().strip()
        if not normalized_query:
            return rows
        filtered: list[dict[str, Any]] = []
        for row in rows:
            item = row["item"]
            card = row["triage_card"] or {}
            haystack = " ".join(
                [
                    str(item["id"]),
                    str(item["title"]),
                    str(item["status"]),
                    str(item["manual_decision"] or ""),
                    str(item["ai_recommendation"] or ""),
                    str(card.get("summary", "")),
                    " ".join(card.get("key_points", [])),
                    str(card.get("recommendation", "")),
                    str(card.get("reason", "")),
                ]
            ).lower()
            if normalized_query in haystack:
                filtered.append(row)
        return filtered

    def _filter_learning_rows(self, rows: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
        normalized_query = query.lower().strip()
        if not normalized_query:
            return rows
        filtered: list[dict[str, Any]] = []
        for row in rows:
            item = row["item"]
            state = row["state"] or {}
            haystack = " ".join(
                [
                    str(item["id"]),
                    str(item["title"]),
                    str(item["status"]),
                    str(row["next_action"]),
                    str(state.get("status", "")),
                    str(state.get("processing_mode", "")),
                    str(state.get("current_focus", "")),
                    str(state.get("next_action", "")),
                    str(state.get("core_summary", "")),
                    " ".join(state.get("focus_history", [])),
                ]
            ).lower()
            if normalized_query in haystack:
                filtered.append(row)
        return filtered

    def _show_learning_details(self, doc_id: str) -> None:
        try:
            item = storage.read_content_item_by_id(doc_id, self.repo_root)
            state = storage.read_learning_state(doc_id, self.repo_root) if storage.learning_state_exists(doc_id, self.repo_root) else None
            queue_entry = storage.get_queue_entry(doc_id, self.repo_root)
            raw_path = storage.resolve_raw_path(item, self.repo_root)
            metadata_path = storage.get_content_item_path(item["source_type"], item["id"], self.repo_root)
            state_path = storage.get_learning_states_root(self.repo_root) / doc_id / "state.json"
            output_dir = storage.get_learning_outputs_root(self.repo_root) / doc_id
            outline_path = output_dir / "outline.md"
            summary_path = output_dir / "summary.md"
            insights_path = output_dir / "insights.md"
            qa_path = output_dir / "qa.md"
            raw_preview = self._raw_preview(item)
            outline_preview = self._preview_file_text(outline_path)
            summary_preview = self._preview_file_text(summary_path)
            insights_preview = self._preview_file_text(insights_path)
            state_preview = self._preview_state(state)
            latest_prompt_path = self._latest_learning_prompt_path(doc_id)
        except Exception as exc:
            self._show_error("Unable to load learning detail", exc)
            return

        if latest_prompt_path is None:
            self.learning_latest_prompt_var.set("Latest learning prompt: none")
        else:
            self.learning_latest_prompt_var.set(f"Latest learning prompt: {latest_prompt_path}")

        lines = [
            f"ID: {item['id']}",
            f"Title: {item['title']}",
            f"Status: {item['status']}",
            f"Queue: {None if queue_entry is None else queue_entry['status']}",
            f"Priority: {item['priority']}",
            f"Raw path: {raw_path}",
            f"Metadata path: {metadata_path}",
            f"State path: {state_path}",
            f"Outline path: {outline_path}",
            f"Summary path: {summary_path}",
            f"Insights path: {insights_path}",
            f"QA path: {qa_path}",
            "",
            "Outline preview:",
            outline_preview,
            "",
            "Summary preview:",
            summary_preview,
            "",
            "Insights preview:",
            insights_preview,
            "",
            "Raw preview:",
            raw_preview,
            "",
            ]
        if state is None:
            lines.append("State: not initialized yet")
        else:
            lines.extend(
                [
                    f"Initialized: {state['initialized']}",
                    f"Processing mode: {state['processing_mode']}",
                    f"Progress: {float(state['progress']) * 100:.0f}%",
                    f"Current focus: {state['current_focus'] or 'none'}",
                    f"Focus history: {len(state['focus_history'])}",
                    f"Interaction count: {state['interaction_count']}",
                    f"Current chunk: {state['current_chunk']}/{state['chunks_total']}",
                    f"Ready to consolidate: {state['ready_to_consolidate']}",
                    f"Outline generated: {state['outline_generated']}",
                    "",
                    "Core summary:",
                    state["core_summary"] or "none",
                    "",
                    "Recent insights:",
                    self._join_lines(state["insights"]) or "none",
                    "",
                    "Next action:",
                    state["next_action"] or "none",
                    "",
                    "State preview:",
                    state_preview,
                ]
            )
        self._set_text(self.learning_detail, "\n".join(lines))

    def _raw_preview(self, item: dict[str, Any], limit: int = 1200) -> str:
        raw_path = storage.resolve_raw_path(item, self.repo_root)
        text_suffixes = {".md", ".txt", ".rst", ".json", ".yaml", ".yml", ".csv", ".tsv", ".py", ".toml", ".html", ".htm", ".xml"}
        if raw_path.suffix.lower() not in text_suffixes:
            return f"Preview unavailable for {raw_path.suffix or 'binary'} files."
        try:
            text = storage.read_raw_text_for_item(item, self.repo_root)
        except Exception as exc:
            return f"Preview unavailable: {exc}"
        normalized = text.strip()
        if not normalized:
            return "Empty text file."
        if len(normalized) > limit:
            return normalized[: limit - 1] + "…"
        return normalized

    def _preview_file_text(self, path: Path, limit: int = 1200) -> str:
        if not path.exists():
            return "Not created yet."
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as exc:
            return f"Preview unavailable: {exc}"
        normalized = text.strip()
        if not normalized:
            return "Empty file."
        if len(normalized) > limit:
            return normalized[: limit - 1] + "…"
        return normalized

    def _preview_state(self, state: dict[str, Any] | None) -> str:
        if state is None:
            return "No learning state yet."
        lines = [
            f"initialized={state['initialized']}",
            f"status={state['status']}",
            f"processing_mode={state['processing_mode']}",
            f"progress={float(state['progress']) * 100:.0f}%",
            f"current_focus={state['current_focus'] or 'none'}",
            f"interaction_count={state['interaction_count']}",
            f"current_chunk={state['current_chunk']}/{state['chunks_total']}",
            f"ready_to_consolidate={state['ready_to_consolidate']}",
            f"outline_generated={state['outline_generated']}",
            f"next_action={state['next_action']}",
        ]
        return "\n".join(lines)

    def _generate_triage_prompt(self) -> None:
        doc_id = self._selected_tree_id(self.triage_tree)
        if doc_id is None:
            return
        self._run_action(
            f"Generate triage prompt for {doc_id}",
            lambda: self._generate_triage_prompt_action(doc_id),
        )

    def _open_selected_triage_raw(self) -> None:
        self._run_selected_triage_file_action("Open raw", lambda raw_path, *_: self._open_path_with_feedback(raw_path, "raw file"))

    def _open_selected_triage_metadata(self) -> None:
        self._run_selected_triage_file_action("Open metadata", lambda _, metadata_path, *__: self._open_path_with_feedback(metadata_path, "metadata file"))

    def _open_selected_triage_card(self) -> None:
        self._run_selected_triage_file_action("Open triage card", lambda *args: self._open_path_with_feedback(args[4], "triage card"))

    def _open_selected_triage_prompt(self) -> None:
        self._run_selected_triage_file_action("Open triage prompt", lambda *args: self._open_path_with_feedback(args[5], "triage prompt"))

    def _copy_selected_triage_paths(self) -> None:
        item, _, raw_path, metadata_path, card_path, prompt_path = self._selected_triage_item()
        self._copy_paths(
            f"triage item {item['id']}",
            [raw_path, metadata_path, card_path, prompt_path],
        )

    def _generate_triage_batch_prompt(self) -> None:
        limit = simpledialog.askinteger("Batch Size", "How many items should go into the triage batch?", minvalue=1, initialvalue=5)
        if limit is None:
            return
        self._run_action(
            "Generate triage batch prompt",
            self._write_triage_batch_prompt(limit),
        )

    def _triage_decision(self, decision: str) -> None:
        doc_id = self._selected_tree_id(self.triage_tree)
        if doc_id is None:
            return

        def action() -> str:
            if decision == "accept":
                triage.accept_candidate(doc_id, self.repo_root)
            elif decision == "reject":
                triage.reject_candidate(doc_id, self.repo_root)
            else:
                triage.defer_candidate(doc_id, self.repo_root)
            return f"Triage decision saved for {doc_id}: {decision}"

        self._run_action(f"Triage {decision} for {doc_id}", action)

    def _publish_triage_card(self) -> None:
        doc_id = self._selected_tree_id(self.triage_tree)
        if doc_id is None:
            return
        self._run_action(
            f"Publish triage card for {doc_id}",
            lambda: f"Published triage card: {publish.publish_triage(doc_id, self.repo_root)}",
        )

    def _generate_learning_prompt(self) -> None:
        doc_id = self._selected_tree_id(self.learning_tree)
        if doc_id is None:
            return
        focus = self.learning_focus_var.get().strip() or None
        mode = learning.resolve_learning_mode(doc_id, self.repo_root)
        self._run_action(
            f"Generate learning prompt for {doc_id}",
            lambda: self._generate_learning_prompt_action(doc_id, mode, focus),
        )

    def _open_selected_learning_raw(self) -> None:
        self._run_selected_learning_file_action("Open raw", lambda raw_path, *_: self._open_path_with_feedback(raw_path, "raw file"))

    def _open_selected_learning_metadata(self) -> None:
        self._run_selected_learning_file_action("Open metadata", lambda _, metadata_path, *__: self._open_path_with_feedback(metadata_path, "metadata file"))

    def _open_selected_learning_state(self) -> None:
        self._run_selected_learning_file_action("Open state", lambda *args: self._open_path_with_feedback(args[4], "state file"))

    def _open_selected_learning_outline(self) -> None:
        self._run_selected_learning_file_action("Open outline", lambda *args: self._open_path_with_feedback(args[6], "outline file"))

    def _open_selected_learning_outputs(self) -> None:
        self._run_selected_learning_file_action("Open outputs", lambda *args: self._open_path_with_feedback(args[5], "outputs folder"))

    def _open_learning_prompt_dir(self) -> None:
        try:
            prompt_dir = storage.get_learning_prompts_root(self.repo_root)
            self._open_path_with_feedback(prompt_dir, "learning prompt directory")
        except Exception as exc:
            self._show_error("Open prompt directory failed", exc)

    def _copy_selected_learning_paths(self) -> None:
        item, _, raw_path, metadata_path, state_path, output_dir, outline_path, summary_path, insights_path, qa_path = self._selected_learning_item()
        self._copy_paths(
            f"learning item {item['id']}",
            [raw_path, metadata_path, state_path, output_dir, outline_path, summary_path, insights_path, qa_path],
        )

    def _generate_next_learning_prompt(self) -> None:
        focus = self.learning_focus_var.get().strip() or None

        def action() -> str:
            target = learning.get_next_learning_target(self.repo_root)
            prompt_path = agent_workflow.write_learning_prompt(
                target["item"]["id"],
                target["mode"],
                focus,
                self.repo_root,
            )
            self._set_learning_latest_prompt(prompt_path)
            self._copy_to_clipboard(str(prompt_path))
            return f"Next learning prompt saved: {prompt_path}"

        self._run_action("Generate next learning prompt", action)

    def _generate_pause_prompt(self) -> None:
        doc_id = self._selected_tree_id(self.learning_tree)
        if doc_id is None:
            return
        self._run_action(
            f"Generate pause prompt for {doc_id}",
            lambda: self._generate_pause_prompt_action(doc_id),
        )

    def _generate_consolidate_prompt(self) -> None:
        doc_id = self._selected_tree_id(self.learning_tree)
        if doc_id is None:
            return
        self._run_action(
            f"Generate consolidate prompt for {doc_id}",
            lambda: self._generate_consolidate_prompt_action(doc_id),
        )

    def _publish_learning_outputs(self) -> None:
        doc_id = self._selected_tree_id(self.learning_tree)
        if doc_id is None:
            return
        self._run_action(
            f"Publish learning outputs for {doc_id}",
            lambda: f"Published learning outputs: {publish.publish_learning(doc_id, self.repo_root)}",
        )

    def _choose_ingest_files(self) -> None:
        paths = filedialog.askopenfilenames(title="Choose files to add")
        if not paths:
            return
        self._append_ingest_paths([Path(path) for path in paths])

    def _handle_drop(self, event: tk.Event) -> None:  # pragma: no cover - drag-drop binding
        try:
            dropped_paths = [Path(path) for path in self.tk.splitlist(event.data)]
        except Exception as exc:
            self._show_error("Unable to parse dropped files", exc)
            return
        self._append_ingest_paths(dropped_paths)

    def _register_drop_target(self, widget: tk.Widget) -> None:
        if not self._drop_enabled:
            return
        try:
            widget.drop_target_register(DND_FILES)  # type: ignore[attr-defined]
            widget.dnd_bind("<<Drop>>", self._handle_drop)  # type: ignore[attr-defined]
        except Exception:
            LOGGER.debug("Drag-and-drop target registration failed for %s", widget, exc_info=True)

    def _append_ingest_paths(self, paths: list[Path]) -> None:
        added = 0
        for path in paths:
            resolved = path.expanduser().resolve()
            if resolved in self.ingest_paths:
                continue
            self.ingest_paths.append(resolved)
            self.ingest_list.insert("end", str(resolved))
            added += 1
        self.add_hint_var.set(f"{added} file(s) added to the ingest list" if added else "No new files added")

    def _clear_ingest_paths(self) -> None:
        self.ingest_paths.clear()
        self.ingest_list.delete(0, "end")
        self.add_hint_var.set("Ingest list cleared")

    def _remove_selected_ingest_paths(self) -> None:
        selected = list(self.ingest_list.curselection())
        if not selected:
            return
        for index in reversed(selected):
            del self.ingest_paths[index]
            self.ingest_list.delete(index)
        self.add_hint_var.set("Removed selected files")

    def _add_selected_files(self) -> None:
        if not self.ingest_paths:
            messagebox.showinfo("Add Content", "Choose one or more files first.")
            return
        ingest_title = self.ingest_title_var.get().strip() or None
        storage_mode = self.ingest_storage_mode_var.get()
        source_type = self.ingest_source_var.get()
        content_type = self.ingest_content_type_var.get()
        explicit_accept = bool(self.ingest_accept_var.get())

        if len(self.ingest_paths) > 1 and ingest_title is not None:
            self._log("Title override applies to one file at a time; using derived titles for multiple files.")
            ingest_title = None

        def action() -> str:
            results: list[str] = []
            for source_path in self.ingest_paths:
                result = self._ingest_one(
                    source_path=source_path,
                    source_type=source_type,
                    content_type=content_type,
                    title=ingest_title,
                    explicit_accept=explicit_accept,
                    storage_mode=storage_mode,
                )
                results.append(result)
            return "\n".join(results)

        self._run_action(f"Ingest {len(self.ingest_paths)} file(s)", action)
        self._clear_ingest_paths()

    def _ingest_one(
        self,
        *,
        source_path: Path,
        source_type: str,
        content_type: str,
        title: str | None,
        explicit_accept: bool,
        storage_mode: str,
    ) -> str:
        self._require_workspace_root()
        plan = ingest_detection.build_ingest_plan(
            source_type=source_type,
            content_type=content_type,
            source_path=source_path,
            explicit_title=title,
            explicit_accept=explicit_accept,
        )

        if storage_mode == "inbox" and plan.is_url_list:
            raise ValueError("raw inbox mode does not support URL list inputs")

        if plan.is_url_list:
            result = url_ingest.ingest_url_list(
                source_type=source_type,
                content_type=content_type,
                url_list_path=source_path,
                initial_status=plan.initial_status,
                root=self.repo_root,
            )
            added = len(result["added_items"])
            duplicates = len(result["duplicate_items"])
            failures = len(result["failures"])
            return (
                f"{source_path.name}: url list ingested | added={added} "
                f"duplicates={duplicates} failures={failures} status={plan.initial_status}"
            )

        content_hash = storage.compute_file_hash(source_path)
        existing_item = storage.find_content_item_by_hash(content_hash, self.repo_root)
        if existing_item is not None:
            return f"{source_path.name}: duplicate item -> {existing_item['id']}"

        doc_id = storage.build_doc_id(plan.title, source_type, self.repo_root)
        if storage_mode == "inbox":
            stored_file_info = storage.ingest_raw_file_to_inbox(doc_id, source_type, source_path, self.repo_root)
        else:
            stored_file_info = storage.ingest_raw_file(doc_id, source_type, source_path, self.repo_root)

        status = plan.initial_status
        recommendation = "learn" if status == "accepted" else "skim"
        item = storage.create_content_item(
            doc_id=doc_id,
            title=plan.title,
            source_type=source_type,
            content_type=content_type,
            ingest_date=datetime.now().date().isoformat(),
            status=status,
            priority=1.0 if source_type == "manual" else 0.5,
            ai_recommendation=recommendation,
            manual_decision=None,
            storage_tier=stored_file_info["storage_tier"],
            full_raw_relpath=stored_file_info["full_raw_relpath"],
            sync_raw_relpath=stored_file_info["sync_raw_relpath"],
            source_filename=stored_file_info["source_filename"],
            source_device=stored_file_info["source_device"],
            content_hash=stored_file_info["content_hash"],
            sync_status=stored_file_info["sync_status"],
        )
        storage.write_content_item(item, self.repo_root)
        if status == "accepted":
            storage.upsert_queue_entry(storage.create_queue_entry(doc_id, item["priority"], "todo"), self.repo_root)
        return (
            f"{source_path.name}: added as {doc_id} | title={plan.title!r} | "
            f"status={status} | storage={item['storage_tier']} | source={storage_mode}"
        )

    def _write_and_copy_prompt(self, prompt_path: Path) -> str:
        self._copy_to_clipboard(str(prompt_path))
        return f"Prompt saved: {prompt_path}"

    def _generate_triage_prompt_action(self, doc_id: str) -> str:
        prompt_path = agent_workflow.write_triage_prompt(doc_id, self.repo_root)
        self._set_triage_latest_prompt(prompt_path)
        self._copy_to_clipboard(str(prompt_path))
        self._open_path_with_feedback(prompt_path, "triage prompt")
        return f"Triage prompt saved and opened: {prompt_path}"

    def _write_triage_batch_prompt(self, limit: int) -> Callable[[], str]:
        def action() -> str:
            prompt_path, selected_ids, total_pending = agent_workflow.write_triage_batch_prompt(limit, self.repo_root)
            self._set_triage_latest_prompt(prompt_path)
            self._copy_to_clipboard(str(prompt_path))
            self._open_path_with_feedback(prompt_path, "triage batch prompt")
            return (
                f"Batch triage prompt saved and opened: {prompt_path}\n"
                f"Selected ids: {', '.join(selected_ids) if selected_ids else 'none'}\n"
                f"Total pending: {total_pending}"
            )

        return action

    def _selected_tree_id(self, tree: ttk.Treeview) -> str | None:
        selection = self._current_tree_selection(tree)
        if not selection:
            messagebox.showinfo("Selection Required", "Select an item in the table first.")
            return None
        return selection

    def _select_tree_item(self, tree: ttk.Treeview, doc_id: str) -> None:
        if tree.exists(doc_id):
            tree.selection_set(doc_id)
            tree.see(doc_id)
            tree.focus(doc_id)

    def _current_tree_selection(self, tree: ttk.Treeview) -> str | None:
        selection = tree.selection()
        return selection[0] if selection else None

    def _restore_tree_selection(
        self,
        tree: ttk.Treeview,
        ordered_ids: list[str],
        previous_selection: str | None,
        detail_loader: Callable[[str], None],
        empty_message: str,
    ) -> None:
        target_id = previous_selection if previous_selection in ordered_ids else (ordered_ids[0] if ordered_ids else None)
        if target_id is None:
            self._set_text(self._detail_widget_for_tree(tree), empty_message)
            self._set_tree_selection_buttons_enabled(tree, False)
            return
        self._select_tree_item(tree, target_id)
        detail_loader(target_id)
        self._set_tree_selection_buttons_enabled(tree, True)

    def _detail_widget_for_tree(self, tree: ttk.Treeview) -> ScrolledText:
        if tree is self.triage_tree:
            return self.triage_detail
        return self.learning_detail

    def _split_dashboard_iid(self, iid: str) -> tuple[str, str]:
        if "::" not in iid:
            return "learn", iid
        return tuple(iid.split("::", 1))  # type: ignore[return-value]

    def _clear_tree(self, tree: ttk.Treeview) -> None:
        for item in tree.get_children():
            tree.delete(item)

    def _set_text(self, widget: ScrolledText, text: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("end", text)
        widget.configure(state="disabled")

    def _preview_text(self, text: str, limit: int = 80) -> str:
        normalized = " ".join(text.split())
        if len(normalized) <= limit:
            return normalized
        return normalized[: limit - 1] + "…"

    def _drop_zone_text(self) -> str:
        if self._drop_enabled:
            return "Drop files here or use the file picker. Drag-and-drop is enabled in this session."
        return "Drop support is not active in this session. Use the file picker, or install tkinterdnd2 to enable drag-and-drop."

    def _format_triage_card(self, card: dict[str, Any] | None) -> str:
        if card is None:
            return "none"
        lines = [
            f"Summary: {card.get('summary', '').strip() or 'none'}",
            "Key points:",
        ]
        key_points = card.get("key_points", [])
        if key_points:
            lines.extend(f"- {point}" for point in key_points)
        else:
            lines.append("- none")
        lines.append(f"Recommendation: {card.get('recommendation', '').strip() or 'none'}")
        lines.append(f"Reason: {card.get('reason', '').strip() or 'none'}")
        return "\n".join(lines)

    def _join_lines(self, values: list[str]) -> str:
        cleaned = [value.strip() for value in values if value and value.strip()]
        return "\n".join(f"- {value}" for value in cleaned)

    def _copy_to_clipboard(self, text: str) -> None:
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update_idletasks()

    def _copy_paths(self, title: str, paths: list[Path | str]) -> None:
        text = "\n".join(str(path) for path in paths)
        self._copy_to_clipboard(text)
        self._log(f"Copied {title} paths to clipboard")

    def _open_path(self, path: Path) -> None:
        target = path if path.exists() else path.parent
        if not target.exists():
            raise FileNotFoundError(target)
        if sys.platform.startswith("win"):
            os.startfile(str(target))  # type: ignore[attr-defined]
            return
        if sys.platform == "darwin":
            subprocess.Popen(["open", str(target)])
            return
        subprocess.Popen(["xdg-open", str(target)])

    def _open_path_with_feedback(self, path: Path, label: str) -> None:
        self._open_path(path)
        self._log(f"Opened {label}: {path}")

    def _selected_triage_item(self) -> tuple[dict[str, Any], dict[str, Any] | None, Path, Path, Path, Path]:
        doc_id = self._selected_tree_id(self.triage_tree)
        if doc_id is None:
            raise ValueError("no triage item selected")
        item = storage.read_content_item_by_id(doc_id, self.repo_root)
        card = triage.read_triage_card(doc_id, self.repo_root)
        raw_path = storage.resolve_raw_path(item, self.repo_root)
        metadata_path = storage.get_content_item_path(item["source_type"], item["id"], self.repo_root)
        card_path = storage.get_triage_cards_root(self.repo_root) / f"{doc_id}.md"
        prompt_path = storage.get_triage_prompts_root(self.repo_root) / f"{doc_id}.md"
        return item, card, raw_path, metadata_path, card_path, prompt_path

    def _selected_learning_item(self) -> tuple[dict[str, Any], dict[str, Any] | None, Path, Path, Path, Path, Path, Path, Path, Path]:
        doc_id = self._selected_tree_id(self.learning_tree)
        if doc_id is None:
            raise ValueError("no learning item selected")
        item = storage.read_content_item_by_id(doc_id, self.repo_root)
        state = storage.read_learning_state(doc_id, self.repo_root) if storage.learning_state_exists(doc_id, self.repo_root) else None
        raw_path = storage.resolve_raw_path(item, self.repo_root)
        metadata_path = storage.get_content_item_path(item["source_type"], item["id"], self.repo_root)
        state_path = storage.get_learning_states_root(self.repo_root) / doc_id / "state.json"
        output_dir = storage.get_learning_outputs_root(self.repo_root) / doc_id
        outline_path = output_dir / "outline.md"
        summary_path = output_dir / "summary.md"
        insights_path = output_dir / "insights.md"
        qa_path = output_dir / "qa.md"
        return item, state, raw_path, metadata_path, state_path, output_dir, outline_path, summary_path, insights_path, qa_path

    def _run_selected_triage_file_action(self, label: str, action: Callable[[dict[str, Any], dict[str, Any] | None, Path, Path, Path, Path], None]) -> None:
        try:
            item, card, raw_path, metadata_path, card_path, prompt_path = self._selected_triage_item()
        except Exception as exc:
            self._show_error(f"{label} failed", exc)
            return

        try:
            action(item, card, raw_path, metadata_path, card_path, prompt_path)
        except Exception as exc:
            self._show_error(f"{label} failed", exc)

    def _run_selected_learning_file_action(
        self,
        label: str,
        action: Callable[[dict[str, Any], dict[str, Any] | None, Path, Path, Path, Path, Path, Path, Path, Path], None],
    ) -> None:
        try:
            selection = self._selected_learning_item()
        except Exception as exc:
            self._show_error(f"{label} failed", exc)
            return

        try:
            action(*selection)
        except Exception as exc:
            self._show_error(f"{label} failed", exc)

    def _browse_directory(self, variable: tk.StringVar) -> None:
        path = filedialog.askdirectory()
        if path:
            variable.set(path)

    def _set_device_name(self) -> None:
        self._run_action(
            "Update device name",
            lambda: self._set_local_config_value(lambda: local_config.set_device_name(self.device_name_var.get(), self.repo_root)),
        )

    def _set_raw_full_root(self) -> None:
        self._run_action(
            "Update raw full root",
            lambda: self._set_local_config_value(lambda: local_config.set_raw_full_root(self.raw_full_root_var.get(), self.repo_root)),
        )

    def _set_raw_sync_root(self) -> None:
        self._run_action(
            "Update raw sync root",
            lambda: self._set_local_config_value(lambda: local_config.set_raw_sync_root(self.raw_sync_root_var.get(), self.repo_root)),
        )

    def _set_workspace_root(self) -> None:
        def action() -> str:
            path = local_config.set_workspace_root(self.workspace_root_var.get(), self.repo_root)
            storage.ensure_storage_layout(self.repo_root)
            self.workspace_root = local_config.get_workspace_root(self.repo_root)
            return f"Workspace root set: {path}"

        self._run_action("Update workspace root", action)

    def _set_obsidian_vault(self) -> None:
        self._run_action(
            "Update Obsidian vault",
            lambda: self._set_local_config_value(lambda: local_config.set_obsidian_vault_path(self.obsidian_vault_var.get(), self.repo_root)),
        )

    def _set_local_config_value(self, setter: Callable[[], Path]) -> str:
        path = setter()
        self._load_config_fields()
        return f"Updated local config: {path}"

    def _set_triage_buttons_enabled(self, enabled: bool) -> None:
        for button in self._triage_selection_buttons:
            self._set_button_enabled(button, enabled)

    def _set_learning_buttons_enabled(self, enabled: bool) -> None:
        for button in self._learning_selection_buttons:
            self._set_button_enabled(button, enabled)

    def _set_tree_selection_buttons_enabled(self, tree: ttk.Treeview, enabled: bool) -> None:
        if tree is getattr(self, "triage_tree", None):
            self._set_triage_buttons_enabled(enabled)
        elif tree is getattr(self, "learning_tree", None):
            self._set_learning_buttons_enabled(enabled)

    def _set_button_enabled(self, button: ttk.Button, enabled: bool) -> None:
        button.state(["!disabled"] if enabled else ["disabled"])

    def _set_triage_latest_prompt(self, prompt_path: Path | None) -> None:
        if prompt_path is None:
            self.triage_latest_prompt_var.set("Latest triage prompt: none")
            return
        self.triage_latest_prompt_var.set(f"Latest triage prompt: {prompt_path}")

    def _latest_triage_prompt_path(self, doc_id: str) -> Path | None:
        prompt_path = storage.get_triage_prompts_root(self.repo_root) / f"{doc_id}.md"
        if prompt_path.exists():
            return prompt_path
        return None

    def _set_learning_latest_prompt(self, prompt_path: Path | None) -> None:
        if prompt_path is None:
            self.learning_latest_prompt_var.set("Latest learning prompt: none")
            return
        self.learning_latest_prompt_var.set(f"Latest learning prompt: {prompt_path}")

    def _latest_learning_prompt_path(self, doc_id: str) -> Path | None:
        prompt_root = storage.get_learning_prompts_root(self.repo_root)
        if not prompt_root.exists():
            return None
        matches = [path for path in prompt_root.glob(f"{doc_id}__*.md") if path.is_file()]
        if not matches:
            return None
        return max(matches, key=lambda path: path.stat().st_mtime)

    def _generate_learning_prompt_action(self, doc_id: str, mode: str, focus: str | None) -> str:
        prompt_path = agent_workflow.write_learning_prompt(doc_id, mode, focus, self.repo_root)
        self._set_learning_latest_prompt(prompt_path)
        self._copy_to_clipboard(str(prompt_path))
        self._open_path_with_feedback(prompt_path, "learning prompt")
        return f"Learning prompt saved and opened: {prompt_path}"

    def _generate_pause_prompt_action(self, doc_id: str) -> str:
        prompt_path = agent_workflow.write_pause_prompt(doc_id, self.repo_root)
        self._set_learning_latest_prompt(prompt_path)
        self._copy_to_clipboard(str(prompt_path))
        return f"Pause prompt saved: {prompt_path}"

    def _generate_consolidate_prompt_action(self, doc_id: str) -> str:
        prompt_path = agent_workflow.write_consolidate_prompt(doc_id, self.repo_root)
        self._set_learning_latest_prompt(prompt_path)
        self._copy_to_clipboard(str(prompt_path))
        return f"Consolidate prompt saved: {prompt_path}"

    def _workspace_ready(self) -> bool:
        try:
            self.workspace_root = local_config.get_workspace_root(self.repo_root)
        except Exception:
            self.workspace_root = None
        return self.workspace_root is not None

    def _require_workspace_root(self, optional: bool = False) -> Path | None:
        workspace_root = local_config.get_workspace_root(self.repo_root)
        if workspace_root is None:
            if optional:
                return None
            raise storage.StorageError("configure workspace_root before using the GUI workflow tabs")
        return workspace_root

    def _auto_refresh(self) -> None:
        try:
            self._refresh_all()
        except Exception as exc:  # pragma: no cover - periodic refresh should not break the app
            LOGGER.exception("Auto refresh failed: %s", exc)
            self._log(f"ERROR Auto refresh failed: {exc}")
            self._set_status("Auto refresh failed")
        finally:
            self.after(AUTO_REFRESH_MS, self._auto_refresh)

    def _refresh_all(self) -> None:
        self.refresh_all()

    def _run_action(self, description: str, func: Callable[[], str]) -> None:
        self._set_status(description)
        try:
            result = func()
        except Exception as exc:
            LOGGER.exception("Action failed: %s", description)
            self._show_error(description, exc)
            self._log(f"ERROR {description}: {exc}")
        else:
            if result:
                self._log(result)
                self._record_recent_operation(result.splitlines()[0])
            else:
                self._log(description)
                self._record_recent_operation(description)
        finally:
            self.refresh_all()

    def _show_error(self, title: str, exc: Exception) -> None:
        message = f"{title}: {exc}"
        LOGGER.error(message)
        messagebox.showerror(title, str(exc))
        self._set_status(f"Error: {title}")

    def _set_status(self, text: str) -> None:
        self.status_var.set(text)
        self.title(f"{APP_TITLE} - {text}")

    def _log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"[{timestamp}] {message}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _record_recent_operation(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {self._preview_text(message, 120)}"
        self.recent_operations.insert(0, entry)
        self.recent_operations = self.recent_operations[:8]
        self._refresh_recent_operations_panel()

    def _refresh_recent_operations_panel(self) -> None:
        if not hasattr(self, "recent_operations_text"):
            return
        if self.recent_operations:
            text = "\n".join(self.recent_operations)
        else:
            text = "No recent operations yet."
        self._set_text(self.recent_operations_text, text)

    def _set_triage_detail(self, text: str) -> None:
        self._set_text(self.triage_detail, text)

    def _set_learning_detail(self, text: str) -> None:
        self._set_text(self.learning_detail, text)


def main(argv: list[str] | None = None) -> int:
    del argv
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s", force=True)
    app = KnowledgeWorkflowApp()
    try:
        app.run()
    except tk.TclError as exc:  # pragma: no cover - GUI startup failure
        LOGGER.error("Unable to start GUI: %s", exc)
        return 1
    return 0
