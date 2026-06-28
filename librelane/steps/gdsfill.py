# Copyright 2025 LibreLane Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os
import shutil
from typing import Optional, Tuple

from .step import ViewsUpdate, MetricsUpdate, Step

from ..config import Variable
from ..state import DesignFormat, State
from ..common import Path, _get_process_limit

from gdsfill.gdsfill import check_klayout_version, fill  # type: ignore
from gdsfill.library.common import PdkInformation, PdkNotSupportedError  # type: ignore


class GdsfillStep(Step):
    config_vars = [
        Variable(
            "GDSFILL_CONFIG",
            Optional[Path],
            "Path to gdsfill configuration file. If not provided, default settings will be used.",
            pdk=True,
        )
    ]


@Step.factory.register()
class Filler(GdsfillStep):
    """
    Generates filler cells using the gdsfill tool and adds them to the GDS.
    Intended as a replacement for KLayout.Filler.
    """

    id = "Gdsfill.Filler"
    name = "Filler Generation (gdsfill)"

    inputs = [DesignFormat.GDS]
    outputs = [DesignFormat.GDS]

    config_vars = GdsfillStep.config_vars + []

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        config = self.config["GDSFILL_CONFIG"]

        try:
            pdk = PdkInformation(self.config["PDK"], config)
        except PdkNotSupportedError:
            self.err(f"PDK not supported by gdsfiller: {self.config['PDK']}")
            return {}, {}

        if not check_klayout_version(pdk):
            self.err(
                f"KLayout version does not meet gdsfill requirements for PDK {self.config['PDK']}."
            )
            return {}, {}

        input_gds = state_in[DesignFormat.GDS]

        output_gds = os.path.join(
            self.step_dir, f"{self.config['DESIGN_NAME']}.{DesignFormat.GDS.extension}"
        )

        shutil.copy(str(input_gds), output_gds)

        fill(
            Path(output_gds),
            pdk,
            keep_data=False,
            dry_run=False,
            max_processes=_get_process_limit(),
        )

        return {DesignFormat.GDS: Path(output_gds)}, {}
