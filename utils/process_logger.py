# -*- coding: utf-8 -*-
import os
import json
import time
import logging
from datetime import datetime
from typing import Optional, Dict, Any

class ProcessLogger:
    """
    Logger de processo com:
      - diretório configurável e cross-platform (fallback: ~/logsgeoref)
      - escrita atômica (arquivo temporário -> replace)
      - acoplamento opcional ao logging do Python (Handler)
      - medição de tempos por fase (start/end)
      - contexto adicional (parâmetros, versões, EPSG etc.)
    """
    def __init__(self, log_directory: Optional[str] = None):
        self.log_lines = []
        self.method_used: Optional[str] = None
        self._timers: Dict[str, float] = {}
        self._handler: Optional[logging.Handler] = None
        self.context: Dict[str, Any] = {}

        # Diretório: usa o recebido; se None, fallback para ~/logsgeoref
        if log_directory is None:
            base_home = os.path.expanduser("~")
            log_directory = os.path.join(base_home, "logsgeoref")
        self.log_directory = os.path.normpath(log_directory)
        os.makedirs(self.log_directory, exist_ok=True)

        # Identificador de execução
        self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Linha de abertura
        self.log(f"=== Início do processo | run_id={self.run_id} ===")

    # ---------- API de logging textual ----------
    def log(self, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_lines.append(f"[{timestamp}] {message}")

    def log_kv(self, **kwargs):
        """Entrada estruturada K=V em JSON compacto ao final da linha para melhor auditoria."""
        if not kwargs:
            return
        payload = json.dumps(kwargs, ensure_ascii=False, separators=(",", ":"))
        self.log(f"DATA {payload}")

    def set_method_used(self, detector_name: str, matcher_name: str, estimator_name: Optional[str] = None):
        """
        Mantém compatibilidade com a assinatura antiga e permite informar o estimador.
        """
        parts = [detector_name, matcher_name]
        if estimator_name:
            parts.append(estimator_name)
        self.method_used = "_".join(parts)

    def set_context(self, **kwargs):
        """Armazena contexto para ser gravado no início do arquivo."""
        self.context.update(kwargs)

    # ---------- Medição de tempos ----------
    def start(self, fase: str):
        self._timers[fase] = time.perf_counter()
        self.log(f"[{fase}] START")

    def end(self, fase: str):
        t0 = self._timers.get(fase)
        if t0 is None:
            self.log(f"[{fase}] END (sem START registrado)")
            return
        dt = time.perf_counter() - t0
        self.log(f"[{fase}] END | elapsed_s={dt:.3f}")
        self.log_kv(fase=fase, elapsed_s=round(dt, 3))
        del self._timers[fase]

    # ---------- Integração com logging do Python ----------
    def attach_python_logging(self, level: int = logging.INFO, logger_name: Optional[str] = None) -> logging.Handler:
        """
        Encaminha mensagens do logging padrão para este ProcessLogger.
        Retorna o handler para permitir detach posterior.
        """
        class _ProcessLoggerHandler(logging.Handler):
            def __init__(self, plog: "ProcessLogger"):
                super().__init__()
                self._plog = plog
            def emit(self, record: logging.LogRecord):
                try:
                    msg = self.format(record)
                except Exception:
                    msg = record.getMessage()
                self._plog.log(msg)

        handler = _ProcessLoggerHandler(self)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        root_logger = logging.getLogger(logger_name)  # None -> root
        root_logger.addHandler(handler)
        root_logger.setLevel(level)
        self._handler = handler
        return handler

    def detach_python_logging(self, logger_name: Optional[str] = None):
        if self._handler is None:
            return
        root_logger = logging.getLogger(logger_name)
        try:
            root_logger.removeHandler(self._handler)
        finally:
            self._handler = None

    # ---------- Escrita em arquivo ----------
    def write_to_file(self, output_path: str) -> str:
        base_name = os.path.splitext(os.path.basename(output_path))[0]
        suffix = f"_{self.method_used}" if self.method_used else ""
        log_path = os.path.join(self.log_directory, f"{base_name}{suffix}_log.txt")

        # Cabeçalho com contexto
        header_lines = []
        if self.context:
            header_lines.append("=== CONTEXT ===")
            for k, v in self.context.items():
                header_lines.append(f"{k}: {v}")
            header_lines.append("=== LOG ===")

        tmp_path = log_path + ".tmp"
        try:
            with open(tmp_path, 'w', encoding='utf-8') as f:
                for line in header_lines:
                    f.write(line + "\n")
                for line in self.log_lines:
                    f.write(line + "\n")
            # escrita atômica
            os.replace(tmp_path, log_path)
        except Exception as e:
            # fallback simples
            try:
                with open(log_path, 'w', encoding='utf-8') as f:
                    for line in header_lines:
                        f.write(line + "\n")
                    for line in self.log_lines:
                        f.write(line + "\n")
            except Exception as e2:
                print(f"Erro ao escrever log em arquivo: {e2}")
        return log_path
