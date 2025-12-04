#!/usr/bin/env -S uv run --with httpx --with typer --with rich --with prompt-toolkit --python 3.13
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "httpx",
#     "typer",
#     "rich",
#     "prompt-toolkit",
# ]
# ///

"""
WhosOnFirst Downloader - Database Download and Management Tool

A CLI tool for downloading and combining WhosOnFirst geographic database files.

Usage:
    Interactive mode (default):
        uv run scripts/wof-download.py

    Command mode:
        uv run scripts/wof-download.py --countries ca,us,mx
        uv run scripts/wof-download.py --countries "Canada" "United States"
        uv run scripts/wof-download.py --list
        uv run scripts/wof-download.py --all
        uv run scripts/wof-download.py --output-dir ./data/wof/
        uv run scripts/wof-download.py --no-combine  # Don't combine databases
        uv run scripts/wof-download.py --combine-only  # Combine existing databases

The tool downloads compressed SQLite databases from geocode.earth and automatically
extracts them to the specified directory. By default, it will combine multiple
databases into a single file for easier access.
"""

import asyncio
import bz2
import sqlite3
import time
from pathlib import Path
from typing import List, Optional, Dict, Set
from dataclasses import dataclass

import httpx
import typer
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    DownloadColumn,
    TransferSpeedColumn,
    TimeRemainingColumn,
    TaskID,
)
from rich.table import Table
from rich.panel import Panel
from rich.box import ROUNDED
from prompt_toolkit import prompt
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document


# Initialize Typer app and Rich console
app = typer.Typer(help="Download WhosOnFirst SQLite database files")
console = Console()


# Country data
COUNTRY_CODES = [
    "ad",
    "ae",
    "af",
    "ag",
    "ai",
    "al",
    "am",
    "ao",
    "aq",
    "ar",
    "as",
    "at",
    "au",
    "aw",
    "ax",
    "az",
    "ba",
    "bb",
    "bd",
    "be",
    "bf",
    "bg",
    "bh",
    "bi",
    "bj",
    "bl",
    "bm",
    "bn",
    "bo",
    "bq",
    "br",
    "bs",
    "bt",
    "bw",
    "by",
    "bz",
    "ca",
    "cc",
    "cd",
    "cf",
    "cg",
    "ch",
    "ci",
    "ck",
    "cl",
    "cm",
    "cn",
    "co",
    "cr",
    "cu",
    "cv",
    "cw",
    "cx",
    "cy",
    "cz",
    "de",
    "dj",
    "dk",
    "dm",
    "do",
    "dz",
    "ec",
    "ee",
    "eg",
    "eh",
    "er",
    "es",
    "et",
    "fi",
    "fj",
    "fk",
    "fm",
    "fo",
    "fr",
    "ga",
    "gb",
    "gd",
    "ge",
    "gf",
    "gg",
    "gh",
    "gi",
    "gl",
    "gm",
    "gn",
    "gp",
    "gq",
    "gr",
    "gs",
    "gt",
    "gu",
    "gw",
    "gy",
    "hk",
    "hn",
    "hr",
    "ht",
    "hu",
    "id",
    "ie",
    "il",
    "im",
    "in",
    "io",
    "iq",
    "ir",
    "is",
    "it",
    "je",
    "jm",
    "jo",
    "jp",
    "ke",
    "kg",
    "kh",
    "ki",
    "km",
    "kn",
    "kp",
    "kr",
    "kw",
    "ky",
    "kz",
    "la",
    "lb",
    "lc",
    "li",
    "lk",
    "lr",
    "ls",
    "lt",
    "lu",
    "lv",
    "ly",
    "ma",
    "mc",
    "md",
    "me",
    "mf",
    "mg",
    "mh",
    "mk",
    "ml",
    "mm",
    "mn",
    "mo",
    "mp",
    "mq",
    "mr",
    "ms",
    "mt",
    "mu",
    "mv",
    "mw",
    "mx",
    "my",
    "mz",
    "na",
    "nc",
    "ne",
    "nf",
    "ng",
    "ni",
    "nl",
    "no",
    "np",
    "nr",
    "nu",
    "nz",
    "om",
    "pa",
    "pe",
    "pf",
    "pg",
    "ph",
    "pk",
    "pl",
    "pm",
    "pn",
    "pr",
    "ps",
    "pt",
    "pw",
    "py",
    "qa",
    "re",
    "ro",
    "rs",
    "ru",
    "rw",
    "sa",
    "sb",
    "sc",
    "sd",
    "se",
    "sg",
    "sh",
    "si",
    "sj",
    "sk",
    "sl",
    "sm",
    "sn",
    "so",
    "sr",
    "ss",
    "st",
    "sv",
    "sx",
    "sy",
    "sz",
    "tc",
    "td",
    "tf",
    "tg",
    "th",
    "tj",
    "tk",
    "tl",
    "tm",
    "tn",
    "to",
    "tr",
    "tt",
    "tv",
    "tw",
    "tz",
    "ua",
    "ug",
    "um",
    "un",
    "us",
    "uy",
    "uz",
    "va",
    "vc",
    "ve",
    "vg",
    "vi",
    "vn",
    "vu",
    "wf",
    "ws",
    "xk",
    "xs",
    "xx",
    "xy",
    "xz",
    "ye",
    "yt",
    "za",
    "zm",
    "zw",
]

COUNTRY_NAMES = [
    "Andorra",
    "United Arab Emirates (الإمارات العربيّة المتّحدة)",
    "Afghanistan (افغانستان)",
    "Antigua and Barbuda",
    "Anguilla",
    "Albania (Shqipëria)",
    "Armenia (Hayastán / Հայաստան)",
    "Angola (Ngola)",
    "Antarctica",
    "Argentina",
    "American Samoa (Amerika Sāmoa)",
    "Austria (Österreich)",
    "Australia",
    "Aruba",
    "Åland Islands (Åland / Ahvenanmaa)",
    "Azerbaijan (Azərbaycan)",
    "Bosnia and Herzegovina (Босна и Херцеговина)",
    "Barbados",
    "Bangladesh (বাংলাদেশ)",
    "Belgium (België / Belgique / Belgien)",
    "Burkina Faso",
    "Bulgaria (Bălgariya / България)",
    "Bahrain (البحرين)",
    "Burundi (Uburundi)",
    "Benin (Bénin)",
    "Saint Barthélemy (Saint-Barthélemy)",
    "Bermuda",
    "Brunei (بروني)",
    "Bolivia (Buliwya / Wuliwya / Volívia)",
    "Bonaire, Sint Eustatius, Saba",
    "Brazil (Brasil)",
    "Bahamas (The Bahamas)",
    "Bhutan (Druk Yul / འབྲུག་ཡུལ)",
    "Botswana",
    "Belarus (Bielaruś / Беларусь)",
    "Belize",
    "Canada",
    "Cocos (Keeling) Islands",
    "Congo (DRC) (République démocratique du Congo)",
    "Central African Republic (Centrafrique / Bêafrîka)",
    "Congo (République du Congo / Repubilika ya Kôngo)",
    "Switzerland (Schweiz / Suisse / Svizzera / Svizra)",
    "Côte d'Ivoire (Ivory Coast)",
    "Cook Islands (Kūki 'Āirani)",
    "Chile",
    "Cameroon (Cameroun)",
    "China (中国)",
    "Colombia",
    "Costa Rica",
    "Cuba",
    "Cabo Verde (Cape Verde)",
    "Curaçao (Kòrsou)",
    "Christmas Island",
    "Cyprus (Κύπρος / Kıbrıs)",
    "Czechia (Česká republika / Česko)",
    "Germany (Deutschland)",
    "Djibouti (جيبوتي)",
    "Denmark (Danmark)",
    "Dominica",
    "Dominican Republic (República Dominicana)",
    "Algeria (ⴷⵣⴰⵢⴻⵔ / الجزائر)",
    "Ecuador",
    "Estonia (Eesti)",
    "Egypt (مصر)",
    "Western Sahara (الجمهورية العربية الصحراوية الديمقراطية)",
    "Eritrea ( إرتريا / ኤርትራ)",
    "Spain (España / Espanya / Espainia)",
    "Ethiopia (ኢትዮጵያ)",
    "Finland (Suomi)",
    "Fiji (Viti / फ़िजी)",
    "Falkland Islands / Malvinas",
    "Micronesia",
    "Faroe Islands (Føroyar / Færøerne)",
    "France",
    "Gabon (République gabonaise)",
    "United Kingdom",
    "Grenada",
    "Georgia (საქართველო)",
    "French Guiana (Guyane)",
    "Guernsey",
    "Ghana (Gaana / Gana)",
    "Gibraltar",
    "Greenland (Kalaallit Nunaat / Grønland)",
    "Gambia (the) (The Gambia)",
    "Guinea (Guinée / Gine)",
    "Guadeloupe",
    "Equatorial Guinea (Guinea Ecuatorial / Guinée équatoriale / Guiné Equatorial)",
    "Greece (Ελλάδα)",
    "South Georgia and the South Sandwich Islands",
    "Guatemala",
    "Guam (Guåhån)",
    "Guinea-Bissau (Guiné-Bissau)",
    "Guyana",
    "Hong Kong (香港)",
    "Honduras",
    "Croatia (Hrvatska)",
    "Haiti (Haïti / Ayiti)",
    "Hungary (Magyarország)",
    "Indonesia",
    "Ireland (Éire)",
    "Israel (ישראל / إسرائيل)",
    "Isle of Man (Ellan Vannin)",
    "India (ભારત / भारत / ಭಾರತ)",
    "British Indian Ocean Territory",
    "Iraq (العراق / عێراق)",
    "Iran (ایران)",
    "Iceland (Ísland)",
    "Italy (Italia)",
    "Jersey (Jèrri)",
    "Jamaica",
    "Jordan (الأردن)",
    "Japan (日本)",
    "Kenya",
    "Kyrgyzstan (Кыргызстан)",
    "Cambodia (កម្ពុជា)",
    "Kiribati",
    "Comoros ( Komori / Comores / جزر القمر)",
    "Saint Kitts and Nevis",
    "Korea (DPR) (조선 / 북조선 / 朝鮮)",
    "Korea (ROK) (한국 / 남한 / 韓國)",
    "Kuwait (دولة الكويت / الكويت)",
    "Cayman Islands",
    "Kazakhstan (Қазақстан)",
    "Laos (ປະເທດລາວ)",
    "Lebanon (لبنان)",
    "Saint Lucia",
    "Liechtenstein",
    "Sri Lanka (ශ්‍රී ලංකාව / இலங்கை)",
    "Liberia",
    "Lesotho",
    "Lithuania (Lietuva)",
    "Luxembourg (Lëtzebuerg / Luxemburg)",
    "Latvia (Latvija)",
    "Libya (ⵍⵉⴱⵢⴰ / ليبيا)",
    "Morocco (ⴰⵎⵔⵔⵓⴽ / ⵍⵎⵖⵔⵉⴱ / المغرب)",
    "Monaco (Múnegu)",
    "Moldova",
    "Montenegro (Црна Гора)",
    "Saint Martin (French part) (Saint-Martin)",
    "Madagascar (Madagasikara)",
    "Marshall Islands (Aorōkin Ṃajeḷ)",
    "North Macedonia (Северна Македонија / Maqedonia e Veriut)",
    "Mali",
    "Myanmar (မြန်မာ)",
    "Mongolia (Монгол Улс / ᠮᠤᠩᠭᠤᠯ / ᠤᠯᠤᠰ)",
    "Macao (澳門)",
    "Northern Mariana Islands (Notte Mariånas)",
    "Martinique",
    "Mauritania (ⵎⵓⵔⵉⵜⴰⵏ / ⴰⴳⴰⵡⵛ / موريتانيا)",
    "Montserrat",
    "Malta",
    "Mauritius (Maurice / Moris)",
    "Maldives (ދިވެހިރާއްޖެ)",
    "Malawi (Malaŵi)",
    "Mexico (México / Mēxihco)",
    "Malaysia",
    "Mozambique (Moçambique)",
    "Namibia (Namibië)",
    "New Caledonia (Nouvelle-Calédonie)",
    "Niger",
    "Norfolk Island (Norf'k Ailen)",
    "Nigeria (Nijeriya / Naìjíríyà / Nàìjíríà)",
    "Nicaragua",
    "Netherlands (Nederland / Nederlân)",
    "Norway (Norge / Noreg / Norga / Vuodna / Nöörje)",
    "Nepal (नेपाल)",
    "Nauru (Naoero)",
    "Niue (Niuē)",
    "New Zealand (Aotearoa)",
    "Oman (عُمان)",
    "Panama (Panamá)",
    "Peru (Perú / Piruw)",
    "French Polynesia (Polynésie française)",
    "Papua New Guinea (Papua New Guinea / Papua Niugini / Papua Niu Gini)",
    "Philippines (Pilipinas)",
    "Pakistan (پاکستان)",
    "Poland (Polska)",
    "Saint Pierre and Miquelon (Saint-Pierre et Miquelon)",
    "Pitcairn (Pitkern Ailen)",
    "Puerto Rico",
    "Palestine (فلسطين)",
    "Portugal",
    "Palau (Belau)",
    "Paraguay (Paraguái)",
    "Qatar (قطر)",
    "Réunion (La Réunion)",
    "Romania (România)",
    "Serbia (Србија)",
    "Russia (Россия)",
    "Rwanda",
    "Saudi Arabia (المملكة العربية السعودية)",
    "Solomon Islands (Solomon Aelan)",
    "Seychelles (Sesel)",
    "Sudan (the) (السودان)",
    "Sweden (Sverige)",
    "Singapore (Singapura / 新加坡 / சிங்கப்பூர்)",
    "Saint Helena, Ascension Island, Tristan da Cunha",
    "Slovenia (Slovenija)",
    "Svalbard and Jan Mayen",
    "Slovakia (Slovensko)",
    "Sierra Leone",
    "San Marino",
    "Senegal (Sénégal / Senegaal)",
    "Somalia (Soomaaliya / الصومال)",
    "Suriname",
    "South Sudan (Sudan Kusini / Paguot Thudän)",
    "Sao Tome and Principe (São Tomé e Príncipe)",
    "El Salvador",
    "Sint Maarten (Dutch part)",
    "Syria (سورية)",
    "Eswatini (eSwatini)",
    "Turks and Caicos Islands",
    "Chad (Tchad / تشاد)",
    "French Southern Territories (Terres australes françaises)",
    "Togo",
    "Thailand (ไทย, ประเทศไทย, ราชอาณาจักรไทย)",
    "Tajikistan (Тоҷикистон)",
    "Tokelau",
    "Timor-Leste (Timor Lorosa'e)",
    "Turkmenistan (Türkmenistan)",
    "Tunisia (ⵜⵓⵏⵙ / تونس)",
    "Tonga",
    "Türkiye (Türkiye)",
    "Trinidad and Tobago",
    "Tuvalu",
    "Taiwan (中華民國 / 臺灣/台灣)",
    "Tanzania",
    "Ukraine (Україна)",
    "Uganda",
    "U.S. Minor Outlying Islands",
    "United Nations (Les Nations Unies)",
    "United States of America (Estados Unidos / 'Amelika Hui Pū 'ia)",
    "Uruguay",
    "Uzbekistan (Ўзбекистон)",
    "Holy See (Civitas Vaticana / Città del Vaticano)",
    "Saint Vincent and the Grenadines",
    "Venezuela",
    "Virgin Islands (British)",
    "Virgin Islands (U.S.)",
    "Viet Nam (Việt Nam)",
    "Vanuatu",
    "Wallis and Futuna (Wallis-et-Futuna / ʻUvea mo Futuna)",
    "Samoa (Sāmoa)",
    "Kosovo (Kosova / Косово)",
    "Somaliland (Soomaaliland / جمهورية صوماليلاند )",
    "Disputed territories (Territoires contestés)",
    "Undetermined country (Pays indéterminé)",
    "Multiple ISO country parents (Parents de plusieurs pays ISO)",
    "Yemen (اليمن)",
    "Mayotte (Maore)",
    "South Africa (Suid-Afrika / iNingizimu Afrika / uMzantsi Afrika / Afrika-Borwa)",
    "Zambia",
    "Zimbabwe",
]


@dataclass(frozen=True)
class Country:
    """Represents a country with its code and name."""

    code: str
    name: str

    @property
    def display_name(self) -> str:
        """Return a formatted display name."""
        # Extract just the primary name (before parentheses)
        primary_name = self.name.split("(")[0].strip()
        return f"{primary_name} ({self.code.upper()})"

    @property
    def search_text(self) -> str:
        """Return searchable text (lowercase for matching)."""
        return f"{self.code} {self.name}".lower()


class CountryManager:
    """Manages country data and search functionality."""

    def __init__(self):
        self.countries = [
            Country(code, name) for code, name in zip(COUNTRY_CODES, COUNTRY_NAMES)
        ]
        self.code_map = {c.code.lower(): c for c in self.countries}
        self.name_map = {c.name.lower(): c for c in self.countries}

    def search(self, query: str) -> List[Country]:
        """Search for countries by code or name with multi-word support."""
        query = query.lower().strip()

        # Exact code match
        if query in self.code_map:
            return [self.code_map[query]]

        # Split query into words for multi-word search
        words = query.split()
        if not words:
            return []

        scored_results = []

        for country in self.countries:
            search_text = country.search_text
            name_lower = country.name.lower()

            # Check if all words match
            match = True
            score = 0
            last_pos = 0

            for i, word in enumerate(words):
                # Find word starting from last position
                pos = search_text.find(word, last_pos)
                if pos == -1:
                    match = False
                    break

                # Score based on position and word index
                if i == 0:
                    # First word matching at beginning of name gets highest score
                    if name_lower.startswith(word):
                        score += 1000
                    # First word matching at beginning of any word in name
                    elif pos > 0 and search_text[pos - 1] == " ":
                        score += 500
                    else:
                        score += 100
                else:
                    # Subsequent words matching in order
                    if pos > last_pos:
                        score += 50
                    # Bonus for words at word boundaries
                    if pos > 0 and search_text[pos - 1] == " ":
                        score += 25

                last_pos = pos + len(word)

            if match:
                # Bonus for exact name match (ignoring case)
                if query == name_lower or query == country.code.lower():
                    score += 10000
                # Bonus for shorter names (more specific matches)
                score -= len(country.name) * 0.1
                scored_results.append((score, country))

        # Sort by score (highest first) and return countries
        scored_results.sort(key=lambda x: x[0], reverse=True)
        return [country for score, country in scored_results]

    def get_by_input(self, input_str: str) -> Optional[Country]:
        """Get a country by code or name input."""
        input_lower = input_str.lower().strip()

        # Try exact code match first
        if input_lower in self.code_map:
            return self.code_map[input_lower]

        # Try exact name match
        if input_lower in self.name_map:
            return self.name_map[input_lower]

        # Try partial name match
        for country in self.countries:
            if input_lower in country.name.lower():
                return country

        return None

    def parse_country_list(self, countries_str: str) -> List[Country]:
        """Parse a comma-separated list of country codes/names."""
        items = [item.strip() for item in countries_str.split(",")]
        countries = []

        for item in items:
            # First try get_by_input for exact matches
            country = self.get_by_input(item)
            if country:
                countries.append(country)
            else:
                # Try search for partial/multi-word matches
                search_results = self.search(item)
                if search_results:
                    # Take the first match
                    countries.append(search_results[0])
                    if len(search_results) > 1:
                        console.print(
                            f"[yellow]Note: '{item}' matched multiple countries, using {search_results[0].display_name}[/yellow]"
                        )
                else:
                    console.print(
                        f"[yellow]Warning: Could not find country '{item}'[/yellow]"
                    )

        return countries


class WOFDownloader:
    """Handles downloading and extraction of WOF database files."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.base_url = "https://data.geocode.earth/wof/dist/sqlite"

    def get_download_url(self, country_code: str) -> str:
        """Generate the download URL for a country."""
        return f"{self.base_url}/whosonfirst-data-admin-{country_code}-latest.db.bz2"

    def get_output_path(self, country_code: str, compressed: bool = False) -> Path:
        """Get the output file path."""
        filename = f"whosonfirst-data-admin-{country_code}-latest.db"
        if compressed:
            filename += ".bz2"
        return self.output_dir / filename

    async def download_country(
        self,
        country: Country,
        progress: Progress,
        task_id: TaskID,
        client: httpx.AsyncClient,
    ) -> bool:
        """Download a single country database."""
        url = self.get_download_url(country.code)
        compressed_path = self.get_output_path(country.code, compressed=True)
        final_path = self.get_output_path(country.code, compressed=False)

        # Skip if already exists
        if final_path.exists():
            progress.update(
                task_id,
                description=f"[bold bright_green]✓[/bold bright_green] {country.display_name} [dim](already exists)[/dim]",
            )
            progress.update(task_id, completed=100, total=100)
            return True

        try:
            # Download the file
            progress.update(
                task_id,
                description=f"[bold cyan]⬇[/bold cyan]  Downloading {country.display_name}",
            )

            async with client.stream("GET", url) as response:
                response.raise_for_status()

                # Get total size if available
                total_size = int(response.headers.get("content-length", 0))
                if total_size:
                    progress.update(task_id, total=total_size)

                # Download to compressed file
                with open(compressed_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        f.write(chunk)
                        progress.advance(task_id, len(chunk))

            # Extract the file
            progress.update(
                task_id,
                description=f"[bold yellow]📦[/bold yellow] Extracting {country.display_name}",
            )
            await self.extract_bz2(compressed_path, final_path)

            # Clean up compressed file
            compressed_path.unlink()

            progress.update(
                task_id,
                description=f"[bold bright_green]✅[/bold bright_green] {country.display_name}",
            )
            return True

        except httpx.HTTPStatusError as e:
            progress.update(
                task_id,
                description=f"[bold red]❌[/bold red] {country.display_name} [dim](HTTP {e.response.status_code})[/dim]",
            )
            return False
        except Exception as e:
            progress.update(
                task_id,
                description=f"[bold red]❌[/bold red] {country.display_name} [dim]({str(e)})[/dim]",
            )
            return False

    async def extract_bz2(self, compressed_path: Path, output_path: Path):
        """Extract a bz2 compressed file."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, self._extract_bz2_sync, compressed_path, output_path
        )

    def _extract_bz2_sync(self, compressed_path: Path, output_path: Path):
        """Synchronous bz2 extraction."""
        with bz2.open(compressed_path, "rb") as f_in:
            with open(output_path, "wb") as f_out:
                for chunk in iter(lambda: f_in.read(1024 * 1024), b""):
                    f_out.write(chunk)

    async def download_batch(self, countries: List[Country], max_concurrent: int = 3):
        """Download multiple countries with progress tracking."""
        if not countries:
            console.print("[yellow]No countries selected for download.[/yellow]")
            return

        # Create HTTP client with timeout
        timeout = httpx.Timeout(60.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                DownloadColumn(),
                TransferSpeedColumn(),
                TimeRemainingColumn(),
                console=console,
            ) as progress:
                # Create tasks for each country
                tasks = []
                for country in countries:
                    task_id = progress.add_task(
                        f"[cyan]⏳[/cyan] {country.display_name}", total=100
                    )
                    tasks.append(
                        self.download_country(country, progress, task_id, client)
                    )

                # Run downloads with limited concurrency
                semaphore = asyncio.Semaphore(max_concurrent)

                async def limited_download(task):
                    async with semaphore:
                        return await task

                results = await asyncio.gather(
                    *[limited_download(task) for task in tasks]
                )

                # Summary
                successful = sum(1 for r in results if r)
                failed = len(results) - successful

                console.print("\n")
                console.print(
                    Panel(
                        (
                            f"[bold bright_green]✅ Successfully downloaded:[/bold bright_green] {successful}\n"
                            f"[bold red]❌ Failed:[/bold red] {failed}"
                            if failed > 0
                            else f"[bold bright_green]✅ All {successful} downloads completed successfully![/bold bright_green]"
                        ),
                        title="[bold white]Download Results[/bold white]",
                        border_style="bright_green" if failed == 0 else "yellow",
                    )
                )


class CountryCompleter(Completer):
    """Custom completer for country search with multi-word support."""

    def __init__(self, country_manager: CountryManager):
        self.country_manager = country_manager

    def get_completions(self, document: Document, complete_event):
        """Get completions based on current input."""
        # Get the full text, not just before cursor
        text = document.text.lower().strip()

        # Don't complete commands but allow empty string for initial suggestions
        if text in ["list", "selected", "clear", "done", "quit"]:
            return

        # Always show suggestions, even for empty or partial strings
        if not text:
            # Show some common countries when no text is entered
            common_countries = ["us", "ca", "gb", "au", "de", "fr", "jp", "cn"]
            matches = [
                self.country_manager.code_map.get(code)
                for code in common_countries
                if code in self.country_manager.code_map
            ]
        else:
            # Always search based on current text
            matches = self.country_manager.search(text)

            # If no matches, try searching with just the first word or partial text
            if not matches and len(text) > 0:
                # Try with progressively shorter strings
                for i in range(len(text), 0, -1):
                    partial = text[:i]
                    matches = self.country_manager.search(partial)
                    if matches:
                        break

        # Always yield completions if we have matches
        if matches:
            for i, country in enumerate(matches[:8]):
                # Display with country name and code
                display = country.display_name

                # The completion text should be the full country name
                # Replace the entire current text
                yield Completion(
                    country.name.split("(")[0].strip(),
                    start_position=-len(document.text),
                    display=display,
                    display_meta=f"({country.code.upper()})",
                )


class InteractiveSelector:
    """Interactive country selector using prompt_toolkit."""

    def __init__(self, country_manager: CountryManager):
        self.country_manager = country_manager
        self.selected_countries: Set[Country] = set()

    def run(self) -> List[Country]:
        """Run the interactive selector."""
        console.print(
            Panel(
                "[bold cyan]🌍 Interactive Country Selector[/bold cyan]\n\n"
                "[bold yellow]Search:[/bold yellow]\n"
                "  📝 Type country codes (e.g., [cyan]'us'[/cyan], [cyan]'ca'[/cyan]) or names\n"
                "  🔍 Multi-word search: type [cyan]'united st'[/cyan] for United States\n"
                "  ➕ Separate multiple selections with commas\n\n"
                "[bold yellow]Commands:[/bold yellow]\n"
                "  [green]list[/green]     - 📋 View all available countries\n"
                "  [green]selected[/green] - ✅ View your current selection\n"
                "  [green]clear[/green]    - 🗑️  Clear all selections\n"
                "  [green]done[/green]     - 🚀 Start downloading\n"
                "  [green]quit[/green]     - ❌ Exit without downloading",
                title="[bold white]Instructions[/bold white]",
                border_style="bright_blue",
                padding=(1, 2),
            )
        )

        # Create custom completer for country search
        completer = CountryCompleter(self.country_manager)

        while True:
            try:
                # Show current selection count with style
                if self.selected_countries:
                    console.print(
                        f"\n[bold bright_green]✨ Currently selected: {len(self.selected_countries)} {' country' if len(self.selected_countries) == 1 else ' countries'}[/bold bright_green]"
                    )

                # Get user input with our custom completer
                # Configure to always show completions
                user_input = prompt(
                    "[bold bright_cyan]🌎 Enter country (or command)[/bold bright_cyan] ➜ ",
                    completer=completer,
                    complete_while_typing=True,  # Show completions while typing
                    complete_style="multi-column",  # Better display
                ).strip()

                if not user_input:
                    continue

                # Handle commands
                if user_input.lower() == "done":
                    if not self.selected_countries:
                        console.print(
                            "[bold yellow]⚠️  No countries selected. Add some countries first.[/bold yellow]"
                        )
                        continue
                    break

                elif user_input.lower() == "quit":
                    console.print("[bold red]❌ Cancelled.[/bold red]")
                    return []

                elif user_input.lower() == "list":
                    self.show_all_countries()

                elif user_input.lower() == "selected":
                    self.show_selected()

                elif user_input.lower() == "clear":
                    self.selected_countries.clear()
                    console.print(
                        "[bold bright_green]🗑️  Selection cleared![/bold bright_green]"
                    )

                else:
                    # Search for countries
                    search_results = self.country_manager.search(user_input)

                    if search_results:
                        # Show top matches
                        if len(search_results) == 1:
                            # Single match - add directly
                            country = search_results[0]
                            if country in self.selected_countries:
                                console.print(
                                    f"[bold yellow]⚠️  {country.display_name} is already selected[/bold yellow]"
                                )
                            else:
                                self.selected_countries.add(country)
                                console.print(
                                    f"[bold bright_green]✅ Added {country.display_name}[/bold bright_green]"
                                )
                        elif len(search_results) <= 5:
                            # Few matches - show all and auto-select if user presses enter
                            console.print(
                                f"\n[bold bright_blue]🔍 Found {len(search_results)} matches:[/bold bright_blue]"
                            )
                            for i, country in enumerate(search_results, 1):
                                marker = (
                                    "[bold bright_green]✓[/bold bright_green]"
                                    if country in self.selected_countries
                                    else " "
                                )
                                console.print(
                                    f"  {marker} [bold white]{i}.[/bold white] [cyan]{country.display_name}[/cyan]"
                                )

                            console.print(
                                "\n[dim]Press Enter to select #1, or type a number (1-{}):[/dim]".format(
                                    len(search_results)
                                )
                            )

                            # Get selection
                            selection = prompt(
                                "[bold yellow]Select[/bold yellow] ➜ "
                            ).strip()

                            if not selection:  # Enter pressed - select first
                                country = search_results[0]
                            elif selection.isdigit():
                                idx = int(selection) - 1
                                if 0 <= idx < len(search_results):
                                    country = search_results[idx]
                                else:
                                    console.print("[red]Invalid selection[/red]")
                                    continue
                            else:
                                continue

                            if country in self.selected_countries:
                                console.print(
                                    f"[bold yellow]⚠️  {country.display_name} is already selected[/bold yellow]"
                                )
                            else:
                                self.selected_countries.add(country)
                                console.print(
                                    f"[bold bright_green]✅ Added {country.display_name}[/bold bright_green]"
                                )
                        else:
                            # Many matches - show top 10
                            console.print(
                                f"\n[cyan]Found {len(search_results)} matches for '{user_input}':[/cyan]"
                            )
                            for i, country in enumerate(search_results[:10], 1):
                                marker = (
                                    "[green]✓[/green]"
                                    if country in self.selected_countries
                                    else " "
                                )
                                console.print(f"  {marker} {i}. {country.display_name}")

                            if len(search_results) > 10:
                                console.print(
                                    f"  [dim]... and {len(search_results) - 10} more[/dim]"
                                )

                            console.print(
                                "\n[yellow]Type a number to select, or be more specific:[/yellow]"
                            )

                            # Get selection
                            selection = prompt(
                                "Select (or press Enter to skip) > "
                            ).strip()

                            if selection.isdigit():
                                idx = int(selection) - 1
                                if 0 <= idx < min(10, len(search_results)):
                                    country = search_results[idx]
                                    if country in self.selected_countries:
                                        console.print(
                                            f"[yellow]{country.display_name} already selected[/yellow]"
                                        )
                                    else:
                                        self.selected_countries.add(country)
                                        console.print(
                                            f"[green]Added {country.display_name}[/green]"
                                        )
                    else:
                        console.print(f"[red]No matches found for '{user_input}'[/red]")

                        # Try to show helpful suggestions based on partial matches
                        console.print("[yellow]Suggestions:[/yellow]")

                        # Get first few characters and search
                        if len(user_input) >= 2:
                            prefix = user_input[:3]
                            partial_matches = []
                            for country in self.country_manager.countries:
                                if prefix.lower() in country.search_text:
                                    partial_matches.append(country)
                                    if len(partial_matches) >= 5:
                                        break

                            if partial_matches:
                                console.print(
                                    "[dim]Countries starting with similar letters:[/dim]"
                                )
                                for country in partial_matches:
                                    console.print(f"  • {country.display_name}")
                            else:
                                console.print(
                                    "[dim]Try typing the first few letters of a country name or code[/dim]"
                                )

            except KeyboardInterrupt:
                console.print("\n[yellow]Cancelled.[/yellow]")
                return []
            except EOFError:
                break

        return list(self.selected_countries)

    def show_all_countries(self):
        """Display all available countries in a table."""
        table = Table(
            title="[bold cyan]🌍 Available Countries[/bold cyan]",
            show_header=True,
            header_style="bold magenta",
            border_style="bright_blue",
            title_style="bold cyan",
            caption=f"[dim]Total: {len(self.country_manager.countries)} countries[/dim]",
            box=ROUNDED,
        )
        table.add_column("Code", style="bold cyan", width=6)
        table.add_column("Country Name", style="white")
        table.add_column("Status", justify="center", width=8)

        for country in self.country_manager.countries:
            status = (
                "[bold bright_green]✓[/bold bright_green]"
                if country in self.selected_countries
                else ""
            )
            table.add_row(
                country.code.upper(), country.name.split("(")[0].strip(), status
            )

        console.print(table)

    def show_selected(self):
        """Display currently selected countries."""
        if not self.selected_countries:
            console.print("[bold yellow]📭 No countries selected yet.[/bold yellow]")
            return

        table = Table(
            title=f"[bold bright_green]✅ Selected Countries ({len(self.selected_countries)})[/bold bright_green]",
            show_header=True,
            header_style="bold magenta",
            border_style="bright_green",
            box=ROUNDED,
            caption="[dim]Ready to download[/dim]",
        )
        table.add_column("#", style="dim", width=4)
        table.add_column("Code", style="bold cyan", width=6)
        table.add_column("Country Name", style="bright_green")

        for i, country in enumerate(
            sorted(self.selected_countries, key=lambda c: c.name), 1
        ):
            table.add_row(
                str(i), country.code.upper(), country.name.split("(")[0].strip()
            )

        console.print(table)


class WOFCombiner:
    """Combines multiple WhosOnFirst SQLite databases into a single database."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.combined_db_path = output_dir / "whosonfirst-combined.db"

    def get_database_info(self, db_path: Path) -> Dict:
        """Get information about a database (size, row counts)."""
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        info = {"path": db_path, "size": db_path.stat().st_size, "tables": {}}

        # Get row counts for each table
        for table in ["spr", "names", "geojson", "ancestors", "concordances"]:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                info["tables"][table] = cursor.fetchone()[0]
            except sqlite3.Error:
                info["tables"][table] = 0

        conn.close()
        return info

    def find_wof_databases(self) -> List[Path]:
        """Find all WhosOnFirst databases in the output directory."""
        # Pattern for WhosOnFirst database files
        wof_pattern = "whosonfirst-data-admin-*-latest.db"
        databases = list(self.output_dir.glob(wof_pattern))

        # Filter out the combined database if it exists
        databases = [db for db in databases if db.name != "whosonfirst-combined.db"]

        return databases

    def combine_databases(self, databases: List[Path], progress_callback=None) -> bool:
        """
        Combine multiple WhosOnFirst databases into one.
        Uses the largest database as the base to minimize data movement.
        """
        if not databases:
            console.print("[yellow]No databases found to combine.[/yellow]")
            return False

        if len(databases) == 1:
            console.print(
                "[yellow]Only one database found. No combining needed.[/yellow]"
            )
            # Rename the single database to combined
            databases[0].rename(self.combined_db_path)
            return True

        # Get info for all databases
        db_infos = [self.get_database_info(db) for db in databases]

        # Sort by size (largest first)
        db_infos.sort(key=lambda x: x["size"], reverse=True)

        # Use the largest as base
        base_db = db_infos[0]
        other_dbs = db_infos[1:]

        console.print("\n[bold cyan]📊 Database Statistics:[/bold cyan]")
        for info in db_infos:
            size_mb = info["size"] / (1024 * 1024)
            total_rows = sum(info["tables"].values())
            console.print(
                f"  • {info['path'].name}: {size_mb:.1f} MB, {total_rows:,} rows"
            )

        console.print(
            f"\n[bold green]✓ Using {base_db['path'].name} as base (largest)[/bold green]"
        )

        # Copy base database to combined location
        console.print("[cyan]📋 Copying base database...[/cyan]")
        import shutil

        shutil.copy2(base_db["path"], self.combined_db_path)

        # Connect to the combined database
        conn = sqlite3.connect(str(self.combined_db_path))
        conn.execute("PRAGMA journal_mode=WAL")  # Better performance for writes
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=10000")
        conn.execute("PRAGMA temp_store=MEMORY")
        cursor = conn.cursor()

        try:
            # Process each additional database
            for i, db_info in enumerate(other_dbs, 1):
                db_path = db_info["path"]
                alias = f"db{i}"

                console.print(f"\n[bold cyan]🔄 Merging {db_path.name}...[/bold cyan]")

                # Attach the database
                cursor.execute(f"ATTACH DATABASE ? AS {alias}", (str(db_path),))

                # Merge each table
                tables = ["spr", "names", "geojson", "ancestors", "concordances"]

                for table in tables:
                    if db_info["tables"].get(table, 0) == 0:
                        continue

                    start_time = time.time()

                    # Get column names for the table
                    cursor.execute(f"PRAGMA table_info({table})")
                    columns = [row[1] for row in cursor.fetchall()]
                    columns_str = ", ".join(columns)

                    # Use INSERT OR REPLACE to handle potential duplicates
                    # For most WOF tables, the 'id' field is the primary identifier
                    query = f"""
                    INSERT OR REPLACE INTO main.{table} ({columns_str})
                    SELECT {columns_str} FROM {alias}.{table}
                    """

                    console.print(
                        f"  → Merging {table}: {db_info['tables'][table]:,} rows...",
                        end="",
                    )
                    cursor.execute(query)
                    conn.commit()

                    elapsed = time.time() - start_time
                    console.print(f" [green]✓[/green] ({elapsed:.1f}s)")

                # Detach the database
                cursor.execute(f"DETACH DATABASE {alias}")

                if progress_callback:
                    progress_callback(i, len(other_dbs))

            # Optimize the combined database
            console.print("\n[cyan]🔧 Optimizing combined database...[/cyan]")
            cursor.execute("VACUUM")
            cursor.execute("ANALYZE")
            conn.commit()

            # Get final statistics
            console.print(
                "\n[bold green]✅ Database combination complete![/bold green]"
            )

            # Show final statistics
            cursor.execute("SELECT COUNT(*) FROM spr")
            total_places = cursor.fetchone()[0]

            final_size = self.combined_db_path.stat().st_size / (1024 * 1024 * 1024)

            console.print("\n[bold cyan]📊 Combined Database Statistics:[/bold cyan]")
            console.print(f"  • File: {self.combined_db_path.name}")
            console.print(f"  • Size: {final_size:.2f} GB")
            console.print(f"  • Total places: {total_places:,}")

            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                console.print(f"  • {table}: {count:,} rows")

            conn.close()
            return True

        except Exception as e:
            console.print(f"\n[bold red]❌ Error combining databases: {e}[/bold red]")
            conn.close()
            # Clean up partial combined database on error
            if self.combined_db_path.exists():
                self.combined_db_path.unlink()
            return False

    async def combine_after_download(self, combine: bool = True):
        """Combine databases after download if requested."""
        if not combine:
            return

        console.print(
            Panel(
                "[bold cyan]🔀 Combining Downloaded Databases[/bold cyan]\n\n"
                "This will merge all country databases into a single file\n"
                "for easier access and better performance.",
                title="[bold white]Database Combination[/bold white]",
                border_style="cyan",
            )
        )

        databases = self.find_wof_databases()

        if not databases:
            console.print("[yellow]No WhosOnFirst databases found to combine.[/yellow]")
            return

        console.print(f"\n[cyan]Found {len(databases)} database(s) to combine:[/cyan]")
        for db in databases:
            size_mb = db.stat().st_size / (1024 * 1024)
            console.print(f"  • {db.name} ({size_mb:.1f} MB)")

        # Run combination
        success = self.combine_databases(databases)

        if success:
            console.print(
                Panel(
                    f"[bold bright_green]✨ Successfully created combined database![/bold bright_green]\n\n"
                    f"[white]📁 Location:[/white] [yellow]{self.combined_db_path}[/yellow]\n"
                    f"[white]💡 Tip:[/white] You can now use this single database file\n"
                    f"    as your WhosOnFirst data source.",
                    title="[bold white]Success[/bold white]",
                    border_style="bright_green",
                )
            )


@app.command()
def main(
    countries: Optional[str] = typer.Option(
        None,
        "--countries",
        "-c",
        help="Comma-separated list of country codes or names to download",
    ),
    list_countries: bool = typer.Option(
        False, "--list", "-l", help="List all available countries"
    ),
    all_countries: bool = typer.Option(
        False, "--all", "-a", help="Download all available countries"
    ),
    output_dir: Path = typer.Option(
        Path("wof-downloads"),
        "--output-dir",
        "-o",
        help="Directory to save downloaded files",
    ),
    max_concurrent: int = typer.Option(
        3, "--max-concurrent", "-m", help="Maximum number of concurrent downloads"
    ),
    combine: bool = typer.Option(
        True,
        "--combine/--no-combine",
        help="Combine downloaded databases into a single file (default: True)",
    ),
    combine_only: bool = typer.Option(
        False,
        "--combine-only",
        help="Only combine existing databases without downloading",
    ),
):
    """
    Download WhosOnFirst SQLite database files.

    If no options are provided, launches interactive mode.
    """

    # Initialize country manager and combiner
    country_manager = CountryManager()
    combiner = WOFCombiner(output_dir)

    # Handle combine-only mode
    if combine_only:
        console.print(
            Panel(
                "[bold cyan]🔀 Combine-Only Mode[/bold cyan]\n\n"
                "Combining existing databases without downloading new ones.",
                title="[bold white]Database Combination[/bold white]",
                border_style="cyan",
            )
        )
        asyncio.run(combiner.combine_after_download(combine=True))
        return

    # Handle list command
    if list_countries:
        table = Table(
            title="[bold cyan]🌍 WhosOnFirst Available Countries[/bold cyan]",
            show_header=True,
            header_style="bold magenta",
            border_style="bright_blue",
            box=ROUNDED,
            caption=f"[dim]Total: {len(country_manager.countries)} countries available for download[/dim]",
        )
        table.add_column("Code", style="bold cyan", width=6)
        table.add_column("Country Name", style="white")

        for country in country_manager.countries:
            table.add_row(country.code.upper(), country.name)

        console.print(table)
        return

    # Determine which countries to download
    countries_to_download = []

    if all_countries:
        countries_to_download = country_manager.countries
        console.print(
            f"[cyan]Preparing to download all {len(countries_to_download)} countries...[/cyan]"
        )

    elif countries:
        # Command mode with specified countries
        countries_to_download = country_manager.parse_country_list(countries)
        if not countries_to_download:
            console.print("[red]No valid countries found in input.[/red]")
            raise typer.Exit(1)

    else:
        # Interactive mode
        selector = InteractiveSelector(country_manager)
        countries_to_download = selector.run()

        if not countries_to_download:
            console.print("[yellow]No countries selected. Exiting.[/yellow]")
            return

    # Show download summary with style
    console.print(
        Panel(
            f"[bold cyan]📦 Preparing to download {len(countries_to_download)} database{'s' if len(countries_to_download) != 1 else ''}[/bold cyan]\n\n"
            f"[white]📁 Output directory:[/white] [yellow]{output_dir.absolute()}[/yellow]\n"
            f"[white]⚡ Max concurrent:[/white] [yellow]{max_concurrent}[/yellow]",
            title="[bold white]Download Summary[/bold white]",
            border_style="cyan",
        )
    )

    # Create downloader and run
    downloader = WOFDownloader(output_dir)

    # Run async download
    asyncio.run(downloader.download_batch(countries_to_download, max_concurrent))

    console.print(
        Panel(
            f"[bold bright_green]✨ Downloads complete![/bold bright_green]\n\n"
            f"[white]📁 Files saved to:[/white] [yellow]{output_dir.absolute()}[/yellow]",
            title="[bold white]Success[/bold white]",
            border_style="bright_green",
        )
    )

    # Combine databases if requested
    if combine and len(countries_to_download) > 1:
        asyncio.run(combiner.combine_after_download(combine=True))
    elif combine and len(countries_to_download) == 1:
        console.print(
            "\n[dim]Skipping combination (only one database downloaded)[/dim]"
        )


if __name__ == "__main__":
    app()
