import csv
import os.path
from typing import Iterator, NamedTuple

from TexSoup import TexSoup

import explanations.directories as directories
from explanations.directories import SOURCES_DIR, get_arxiv_ids, sources
from explanations.file_utils import clean_directory, find_files, read_file_tolerant
from explanations.types import FileContents
from scripts.command import Command


class Equation(NamedTuple):
    i: int
    tex: str


class ExtractEquations(Command[FileContents, Equation]):
    @staticmethod
    def get_name() -> str:
        return "extract-equations"

    @staticmethod
    def get_description() -> str:
        return "Extract all equations from TeX sources"

    def load(self) -> Iterator[FileContents]:
        for arxiv_id in get_arxiv_ids(SOURCES_DIR):
            sources_dir = sources(arxiv_id)
            clean_directory(directories.equations(arxiv_id))
            for path in find_files(sources_dir, [".tex"]):
                contents = read_file_tolerant(path)
                if contents is None:
                    continue
                yield FileContents(arxiv_id, path, contents)

    def process(self, item: FileContents) -> Iterator[Equation]:
        soup = TexSoup(item.contents)
        # TODO(andrewhead): also find all begin / end equation environments.
        equations = list(soup.find_all("$"))
        for i, equation in enumerate(equations):
            yield Equation(i, equation)

    def save(self, item: FileContents, result: Equation) -> None:
        results_dir = directories.equations(item.arxiv_id)
        if not os.path.exists(results_dir):
            os.makedirs(results_dir)
        results_path = os.path.join(results_dir, "equations.csv")
        with open(results_path, "a") as results_file:
            writer = csv.writer(results_file, quoting=csv.QUOTE_ALL)
            writer.writerow([item.path, result.i, result.tex])
