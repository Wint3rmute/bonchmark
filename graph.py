import datetime
import json
import sys
from datetime import datetime, timedelta
from functools import reduce
from pathlib import Path
from typing import Union, Dict, List, Tuple

from cycler import cycler
from matplotlib import pyplot as plt

PLOT_COLORS_COUNT = 10
GRAPH_TITLE = "Bonchmark"

def recursive_get(obj_input, *keys):
    return reduce(lambda acc, key: acc.get(key, {}), keys, obj_input)


class TemperatureMeasurementLog:
    _JSON_KEYS_TEMPERATURE: List[str] = [
        "coretemp-isa-0000",
        "Package id 0",
        "temp1_input",
    ]

    def __init__(self, path_log_dir: Union[Path, str]):
        """
        Parameters
        ----------
        path_log_dir : Path or str
            Path to directory containing temperature log files.
        """
        path_log_dir = Path(path_log_dir)  # Ensure pathlib.Path type.

        self.name = path_log_dir.stem

        # Maps measurement date to temperature.
        self._entries: Dict[datetime, float] = {}

        # Process all log files and add them as log entries.
        for path_file in Path(path_log_dir).iterdir():
            self._add_measurement(path_file)

    def __repr__(self):
        return "{cls_name}(name='{name}')".format(
            cls_name=self.__class__.__name__, name=self.name
        )

    def _add_measurement(self, path_log_file: Path):
        """ Adds temperature mapped to the corresponding date.

        Parameters
        ----------
        path_log_file : Path
            Path to file containing JSON 'sensors' output.

        Raises
        ------
        IsADirectoryError
            If the specified `path_log_file` is a directory.
        """
        if not path_log_file.is_file():
            raise IsADirectoryError(
                "{} is a directory. Expected a JSON file.".format(path_log_file)
            )

        # Get temperature
        temperature = self._get_temp_from_json(path_json=path_log_file)

        # Parse timestamp into a datetime object.
        hms_str, nanos_str = (
            path_log_file.stem[:8],
            path_log_file.stem[9:],
        )  # Split string into HMS and nanoseconds chunks
        date_measurement = datetime.strptime(hms_str, "%H_%M_%S")
        timedelta_micros = timedelta(microseconds=int(nanos_str) / 1000)
        date_measurement += timedelta_micros

        self._entries[date_measurement] = temperature

    @property
    def date_start(self) -> datetime:
        """ Returns measurement start date
        Returns
        -------
        datetime
            Measurement start date.
        """
        return min(list(self._entries.keys()))

    @property
    def date_stop(self) -> datetime:
        """ Returns measurement stop date
        Returns
        -------
        datetime
            Measurement stop date.
        """
        return max(list(self._entries.keys()))

    @property
    def temperature_min(self):
        return min(list(self._entries.values()))

    @property
    def temperature_max(self):
        return max(list(self._entries.values()))

    @property
    def duration(self) -> float:
        """ Returns measurement duration in seconds.

        Returns
        -------
        float
            Measurement duration in seconds.
        """
        return (self.date_stop - self.date_start).total_seconds()

    def scales(self) -> Tuple[List[float], List[float]]:
        """ Returns pyplot-compatible tuple of lists as (scalex, scaley).

        Measurement times_since_measurements_start are shifted to be relative to the original start date.

        Returns
        -------
        tuple
            Tuple of times_since_measurements_start and temperatures, sorted in relation to time.
        """
        # Get sorted timestamps and corresponding temperatures.
        times_since_measurements_start = sorted(list(self._entries.keys()))
        temperatures = [
            self._entries[date] for date in times_since_measurements_start
        ]

        # Values expressed in seconds.
        times_since_measurements_start = [
            (date - self.date_start).total_seconds()
            for date in times_since_measurements_start
        ]

        return times_since_measurements_start, temperatures

    @staticmethod
    def _get_temp_from_json(path_json: Union[Path, str]) -> float:
        path_abs = str(Path(path_json).resolve())
        with open(path_abs, "r") as istream:
            doc = json.load(istream)

        # noinspection PyTypeChecker
        temperature = float(
            recursive_get(
                doc, *TemperatureMeasurementLog._JSON_KEYS_TEMPERATURE
            )
        )

        return temperature


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise ValueError("Please specify paths to directories containing measurement logs.")
    args_input = sys.argv[1:]

    for path in args_input:
        if not Path(path).is_dir():
            raise NotADirectoryError(
                "{} is not a directory. Please specify only directory paths.".format(
                    path
                )
            )

    measurement_logs = [
        TemperatureMeasurementLog(path_log_dir=path) for path in args_input
    ]

    cm = plt.get_cmap("gist_rainbow")
    fig = plt.figure(figsize=(12, 8), dpi=300, facecolor="w", edgecolor="k")
    ax = fig.add_subplot(111)
    ax.set_title(GRAPH_TITLE)
    ax.set_prop_cycle(cycler("color", ["r", "g", "b", "y", "c", "m", "y", "k"]))

    for index, log in enumerate(measurement_logs):
        ax.plot(*log.scales(), label=log.name)

    plt.rc("grid", linestyle="-", color="black")
    plt.grid(True)
    plt.legend(loc="upper left")
    plt.xlabel("Time [s]")
    plt.ylabel("Temp [°C]")
    # plt.show()

    path_graph = "{}.png".format(str(datetime.now()).replace(" ", "_"))
    print("Saving graph to: {}".format(str(Path(path_graph).resolve())))
    plt.savefig(path_graph)
