from pathlib import Path
from typing import Literal


TSeachMethod = Literal["fnmatch", "re"]

case_sensitive = True
cli_log_level = "INFO"
cli_out_dir = Path.cwd()
cli_session = ""
comp_keys = ["SeriesNumber", "AcquisitionTime"]
defaceTpl = None
log_level = "WARNING"
out_dir = cli_out_dir
search_method: TSeachMethod = "fnmatch"
search_method_choices = ["fnmatch", "re"]
session = cli_session
run_tpl = "_run-{:02d}"
d2b_dir_name = "tmp_d2b"
