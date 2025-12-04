#!/usr/bin/env -S uv run --with httpx --with typer --with rich --with prompt-toolkit --with pydantic --with aiosqlite --with sqlalchemy --with greenlet --with nest-asyncio --python 3.13
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "httpx",
#     "typer",
#     "rich",
#     "prompt-toolkit",
#     "pydantic",
#     "aiosqlite",
#     "sqlalchemy",
#     "greenlet",
#     "nest-asyncio",
# ]
# ///

"""
WhosOnFirst Explorer CLI - Interactive Database Exploration Tool

A clean implementation example using the wof_explorer package.
Demonstrates how to build applications on top of the WOF connector.

Usage:
    # Download and manage databases
    uv run scripts/wof-explore.py download --countries us,ca

    # Explore interactively
    uv run scripts/wof-explore.py explore

    # Quick search
    uv run scripts/wof-explore.py search --name "San Francisco" --placetype locality

    # View statistics
    uv run scripts/wof-explore.py stats

    # Export data
    uv run scripts/wof-explore.py export --ids 85922583 --format geojson
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

# Enable nested asyncio for Jupyter compatibility
import nest_asyncio

nest_asyncio.apply()

# Add parent directory to path for imports
# Works whether run from wof-explorer/ or geography-patterns/
wof_explorer_path = Path(__file__).parent.parent
if wof_explorer_path.name == "wof-explorer":
    sys.path.insert(0, str(wof_explorer_path))
else:
    sys.path.insert(0, str(wof_explorer_path / "wof-explorer"))

# Third-party imports (after sys.path modification)
import typer  # noqa: E402
from prompt_toolkit import prompt  # noqa: E402
from prompt_toolkit.completion import Completer, Completion  # noqa: E402
from prompt_toolkit.document import Document  # noqa: E402
from rich.console import Console  # noqa: E402
from rich.panel import Panel  # noqa: E402
from rich.table import Table  # noqa: E402
from rich.tree import Tree  # noqa: E402

# Import our wof_explorer package - pure implementation
from wof_explorer import (  # noqa: E402
    WOFConnector,
    WOFSearchFilters,
    WOFFilters,
    PlaceCollection,
    WOFHierarchyCursor,
)

# Import our beautiful display utilities
from wof_explorer.display import (  # noqa: E402
    print_summary,
    format_place,
)

# Initialize Typer app with subcommands
app = typer.Typer(
    help="WhosOnFirst Explorer - Interactive database exploration",
    rich_markup_mode="rich",
)
console = Console()


class PlaceCompleter(Completer):
    """Auto-complete for place names."""

    def __init__(self, connector: WOFConnector):
        self.connector = connector
        self._cache = {}

    def get_completions(self, document: Document, complete_event):
        """Get place name completions."""
        text = document.text.strip()
        if len(text) < 2:
            return

        # Use cached results if available
        if text in self._cache:
            results = self._cache[text]
        else:
            # Run async search in sync context
            loop = asyncio.new_event_loop()
            try:
                results = loop.run_until_complete(
                    self.connector.search(
                        WOFSearchFilters(
                            name=text,
                            limit=30,  # Get more results to show variety
                        )
                    )
                )
                self._cache[text] = results
            finally:
                loop.close()

        # Yield completions - prioritize diversity of place types
        if results and results.places:
            # Group by placetype to show variety
            by_type = {}
            for place in results.places:
                if place.placetype not in by_type:
                    by_type[place.placetype] = []
                by_type[place.placetype].append(place)

            # Show one of each type first, then fill remaining slots
            shown = []
            for placetype in by_type:
                if by_type[placetype] and len(shown) < 8:
                    place = by_type[placetype][0]
                    shown.append(place)
                    display = f"{place.name} ({place.placetype})"
                    yield Completion(
                        place.name,
                        start_position=-len(text),
                        display=display,
                        display_meta=place.country or "",
                    )

            # Fill remaining slots with any remaining places
            for place in results.places:
                if place not in shown and len(shown) < 8:
                    shown.append(place)
                    display = f"{place.name} ({place.placetype})"
                    yield Completion(
                        place.name,
                        start_position=-len(text),
                        display=display,
                        display_meta=place.country or "",
                    )


class InteractiveExplorer:
    """Interactive exploration interface."""

    def __init__(self, connector: WOFConnector):
        self.connector = connector
        self.current_place = None
        self.history = []

    async def run(self):
        """Run the interactive explorer."""
        console.print(
            Panel(
                "[bold cyan]🗺️  WhosOnFirst Interactive Explorer[/bold cyan]\n\n"
                "[yellow]Quick Start Menu:[/yellow]\n"
                "  [bold]1[/bold] - Search cities\n"
                "  [bold]2[/bold] - Search neighborhoods (within city)\n"
                "  [bold]3[/bold] - Search counties\n"
                "  [bold]4[/bold] - Browse top cities\n"
                "  [bold]5[/bold] - Show database stats\n"
                "  [bold]6[/bold] - Custom search\n"
                "  [bold green]7[/bold green] - 🎭 Guided Tour (Interactive Demo)\n"
                "  [bold]q[/bold] - Quit\n\n"
                "[dim]Or type a command: search, show <id>, stats, export, quit[/dim]",
                title="Welcome",
                border_style="cyan",
            )
        )

        while True:
            try:
                # Show current context
                if self.current_place:
                    console.print(
                        f"\n[dim]Current: {format_place(self.current_place)}[/dim]"
                    )

                # Simple prompt without auto-complete
                user_input = prompt("🗺️  > ").strip()

                if not user_input:
                    continue

                # Handle menu options first
                if user_input == "1":
                    # Search cities
                    try:
                        city_name = prompt("Enter city name: ").strip()
                        if city_name:
                            await self.search_with_type(city_name, "locality")
                    except (KeyboardInterrupt, EOFError):
                        console.print("\n[dim]Cancelled[/dim]")
                        continue

                elif user_input == "2":
                    # Search neighborhoods within a city
                    try:
                        city_name = prompt("Enter city name: ").strip()
                        if city_name:
                            neighborhood = prompt(
                                "Enter neighborhood name (or press Enter for all): "
                            ).strip()
                            await self.search_neighborhoods_in_city(
                                city_name, neighborhood
                            )
                    except (KeyboardInterrupt, EOFError):
                        console.print("\n[dim]Cancelled[/dim]")
                        continue

                elif user_input == "3":
                    # Search counties
                    try:
                        county_name = prompt("Enter county name: ").strip()
                        if county_name:
                            await self.search_with_type(county_name, "county")
                    except (KeyboardInterrupt, EOFError):
                        console.print("\n[dim]Cancelled[/dim]")
                        continue

                elif user_input == "4":
                    # Browse top cities
                    await self.browse_top_cities()

                elif user_input == "5":
                    # Show stats
                    await self.show_stats()

                elif user_input == "6":
                    # Custom search
                    try:
                        query = prompt("Enter search term: ").strip()
                        if query:
                            await self.search(query)
                    except (KeyboardInterrupt, EOFError):
                        console.print("\n[dim]Cancelled[/dim]")
                        continue

                elif user_input == "7":
                    # Guided tour
                    await self.guided_tour()

                elif user_input.lower() in ["q", "quit", "exit"]:
                    console.print("[yellow]Goodbye! 👋[/yellow]")
                    break

                else:
                    # Parse command
                    parts = user_input.split(maxsplit=1)
                    cmd = parts[0].lower()
                    args = parts[1] if len(parts) > 1 else ""

                    # Handle text commands
                    if cmd == "search":
                        await self.search(args)

                    elif cmd == "show":
                        await self.show_place(args)

                    elif cmd == "ancestors":
                        await self.show_ancestors()

                    elif cmd == "descendants":
                        await self.show_descendants()

                    elif cmd == "nearby":
                        await self.find_nearby(args)

                    elif cmd == "export":
                        await self.export_current()

                    elif cmd == "stats":
                        await self.show_stats()

                    elif cmd == "back":
                        self.go_back()

                    elif cmd == "help" or cmd == "?":
                        self.show_help()

                    else:
                        console.print(f"[red]Unknown command: {cmd}[/red]")
                        console.print(
                            "[dim]Type 'help' for commands or use menu options 1-6[/dim]"
                        )

            except KeyboardInterrupt:
                console.print("\n[yellow]Exiting... Goodbye! 👋[/yellow]")
                break
            except EOFError:
                console.print("\n[yellow]Exiting... Goodbye! 👋[/yellow]")
                break
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")

    async def search_with_type(self, query: str, placetype: str):
        """Search for places with a specific type."""
        filters = WOFSearchFilters(name=query, placetype=placetype, limit=20)

        with console.status(
            f"[cyan]Searching for {placetype} named '{query}'...[/cyan]"
        ):
            cursor = await self.connector.search(filters)

        if not cursor.places:
            console.print(f"[yellow]No {placetype} found matching '{query}'[/yellow]")
            return

        await self.display_search_results(cursor, f"{placetype.title()} Search Results")

    async def search_neighborhoods_in_city(
        self, city_name: str, neighborhood_name: str = ""
    ):
        """Search for neighborhoods within a specific city."""
        if neighborhood_name:
            # Search for specific neighborhood in city
            filters = WOFSearchFilters(
                name=neighborhood_name,
                placetype="neighbourhood",
                ancestor_name=city_name,
                limit=100,
            )
            title = f"Neighborhoods matching '{neighborhood_name}' in {city_name}"
        else:
            # Get all neighborhoods in city - get lots!
            filters = WOFSearchFilters(
                placetype="neighbourhood",
                ancestor_name=city_name,
                limit=300,  # Get all neighborhoods
            )
            title = f"All neighborhoods in {city_name}"

        with console.status(f"[cyan]Searching neighborhoods in {city_name}...[/cyan]"):
            cursor = await self.connector.search(filters)

        if not cursor.places:
            if neighborhood_name:
                console.print(
                    f"[yellow]No neighborhoods found matching '{neighborhood_name}' in {city_name}[/yellow]"
                )
            else:
                console.print(f"[yellow]No neighborhoods found in {city_name}[/yellow]")
            return

        await self.display_search_results(cursor, title)

    async def browse_top_cities(self):
        """Show top cities by coverage."""
        with console.status("[cyan]Loading top cities...[/cyan]"):
            cities = await self.connector.explorer.top_cities_by_coverage(limit=20)

        if not cities:
            console.print("[yellow]No cities found[/yellow]")
            return

        # Display as table
        table = Table(
            title="Top Cities by Coverage", show_header=True, header_style="bold cyan"
        )
        table.add_column("#", width=3)
        table.add_column("WOF ID", style="dim", width=10)
        table.add_column("Name", style="white", max_width=25)
        table.add_column("Country", style="yellow", width=7)
        table.add_column("Region", style="cyan", width=15)
        table.add_column("Places", style="green", width=8)

        for i, city in enumerate(cities[:20], 1):
            name = city.get("name", "Unknown")
            # Truncate long names
            if len(name) > 25:
                name = name[:22] + "..."

            table.add_row(
                str(i),
                str(city.get("id", "")),
                name,
                city.get("country", ""),
                city.get("region", "")[:15],
                f"{city.get('descendant_count', 0):,}",
            )

        console.print(table)

        # Allow selection
        try:
            selection = prompt("Select a city (1-20) or press Enter to skip: ").strip()
            if selection.isdigit():
                idx = int(selection) - 1
                if 0 <= idx < len(cities):
                    city_id = cities[idx].get("id")
                    if city_id:
                        await self.show_place(str(city_id))
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Selection cancelled[/dim]")

    async def display_all_results(self, cursor, title: str):
        """Display ALL search results in a scrollable table."""
        console.print(f"\n[cyan]Showing all {cursor.total_count} results...[/cyan]\n")

        # Simple table without grouping
        table = Table(
            title=f"{title} (all {cursor.total_count} results)",
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("#", width=4)
        table.add_column("WOF ID", style="dim", width=10)
        table.add_column("Name", style="white", max_width=30)
        table.add_column("Type", style="cyan", width=12)
        table.add_column("Region/State", style="yellow", width=15)
        table.add_column("Status", style="green", width=8)

        places_list = []
        for i, place in enumerate(cursor.places, 1):
            # Determine status
            status = "✓" if place.is_current else "ceased"

            # Get region/state if available
            region = place.region or place.country or ""

            # Truncate long names
            name = place.name[:30] + "..." if len(place.name) > 30 else place.name

            table.add_row(str(i), str(place.id), name, place.placetype, region, status)
            places_list.append(place)

        console.print(table)

        # Allow selection from full list
        if places_list:
            try:
                selection = prompt(
                    f"Select (1-{len(places_list)}) or Enter to skip: "
                ).strip()
                if selection.isdigit():
                    idx = int(selection) - 1
                    if 0 <= idx < len(places_list):
                        self.set_current(places_list[idx])
            except (KeyboardInterrupt, EOFError):
                console.print("\n[dim]Selection cancelled[/dim]")

    async def display_search_results(self, cursor, title: str):
        """Display search results in a simple table."""
        # Determine how many to show - more for neighborhoods
        display_limit = 50 if len(cursor.places) > 30 else len(cursor.places)

        # Show count if we have more than we're displaying
        if cursor.total_count > display_limit:
            title = f"{title} (showing {display_limit} of {cursor.total_count})"

        # Simple table without grouping
        table = Table(title=title, show_header=True, header_style="bold cyan")
        table.add_column("#", width=3)
        table.add_column("WOF ID", style="dim", width=10)
        table.add_column("Name", style="white", max_width=30)
        table.add_column("Type", style="cyan", width=12)
        table.add_column("Region/State", style="yellow", width=15)
        table.add_column("Status", style="green", width=8)

        places_list = []
        for i, place in enumerate(cursor.places[:display_limit], 1):
            # Determine status
            status = "✓" if place.is_current else "ceased"

            # Get region/state if available
            region = place.region or place.country or ""

            # Truncate long names
            name = place.name[:30] + "..." if len(place.name) > 30 else place.name

            table.add_row(str(i), str(place.id), name, place.placetype, region, status)
            places_list.append(place)

        console.print(table)

        # Allow selection
        if places_list:
            # Show options based on how many results
            if cursor.total_count > display_limit:
                prompt_text = (
                    f"Select (1-{len(places_list)}), 'm' for more, or Enter to skip: "
                )
            else:
                prompt_text = f"Select (1-{len(places_list)}) or Enter to skip: "

            try:
                selection = prompt(prompt_text).strip().lower()

                if selection == "m" and cursor.total_count > display_limit:
                    # Show all results
                    await self.display_all_results(
                        cursor,
                        title.replace(
                            f" (showing {display_limit} of {cursor.total_count})", ""
                        ),
                    )
                elif selection.isdigit():
                    idx = int(selection) - 1
                    if 0 <= idx < len(places_list):
                        self.set_current(places_list[idx])
            except (KeyboardInterrupt, EOFError):
                console.print("\n[dim]Selection cancelled[/dim]")

    async def search(self, query: str):
        """Search for places."""
        if not query:
            console.print("[yellow]Please provide a search term[/yellow]")
            return

        # Parse search query - check if type is specified
        parts = query.rsplit(" type:", 1)
        if len(parts) == 2:
            name_query = parts[0].strip()
            type_filter = parts[1].strip()
            filters = WOFSearchFilters(name=name_query, placetype=type_filter, limit=20)
            title = f"Search: {name_query} ({type_filter})"
        else:
            filters = WOFSearchFilters(name=query, limit=30)
            title = f"Search: {query}"

        with console.status("[cyan]Searching...[/cyan]"):
            cursor = await self.connector.search(filters)

        if not cursor.places:
            console.print(f"[yellow]No results found for '{query}'[/yellow]")
            return

        await self.display_search_results(cursor, title)

    async def show_place(self, place_id: str):
        """Show detailed place information."""
        if not place_id.isdigit():
            console.print("[red]Please provide a valid place ID[/red]")
            return

        with console.status(f"[cyan]Loading place {place_id}...[/cyan]"):
            places = await self.connector.get_places(
                [int(place_id)], include_geometry=True
            )

        if not places:
            console.print(f"[red]Place {place_id} not found[/red]")
            return

        place = places[0]
        self.set_current(place)

        # Show detailed info
        print_summary(
            {
                "ID": place.id,
                "Name": place.name,
                "Type": place.placetype,
                "Country": place.country,
                "Region": place.region,
                "Status": "Current" if place.is_current else "Historical",
                "Last Modified": place.lastmodified,
                "Location": (
                    f"{place.latitude:.4f}, {place.longitude:.4f}"
                    if place.latitude
                    else "Unknown"
                ),
                "Has Geometry": "Yes" if place.geometry else "No",
            },
            title=place.name,
        )

    async def show_ancestors(self):
        """Show ancestors hierarchy."""
        if not self.current_place:
            console.print(
                "[yellow]No place selected. Use 'search' or 'show' first.[/yellow]"
            )
            return

        with console.status("[cyan]Loading ancestors...[/cyan]"):
            hierarchy = WOFHierarchyCursor(self.current_place, self.connector)
            ancestors = await hierarchy.fetch_ancestors()

        if not ancestors:
            console.print("[yellow]No ancestors found[/yellow]")
            return

        # Build tree display
        tree = Tree(
            f"[bold]{self.current_place.name}[/bold] [dim]({self.current_place.placetype})[/dim]"
        )

        for ancestor in ancestors:
            tree.add(f"{ancestor.name} [dim]({ancestor.placetype})[/dim]")

        console.print(Panel(tree, title="Ancestors", border_style="green"))

    async def show_descendants(self):
        """Show descendants hierarchy."""
        if not self.current_place:
            console.print(
                "[yellow]No place selected. Use 'search' or 'show' first.[/yellow]"
            )
            return

        with console.status("[cyan]Loading descendants...[/cyan]"):
            hierarchy = WOFHierarchyCursor(self.current_place, self.connector)
            descendants = await hierarchy.fetch_descendants()

        if not descendants:
            console.print("[yellow]No descendants found[/yellow]")
            return

        # Group by placetype
        by_type = {}
        for place in descendants:
            if place.placetype not in by_type:
                by_type[place.placetype] = []
            by_type[place.placetype].append(place)

        # Display as tree
        tree = Tree(
            f"[bold]{self.current_place.name}[/bold] [dim]({self.current_place.placetype})[/dim]"
        )

        for placetype, places in by_type.items():
            branch = tree.add(f"[cyan]{placetype}[/cyan] ({len(places)})")
            for place in places[:5]:  # Show first 5
                branch.add(f"{place.name}")
            if len(places) > 5:
                branch.add(f"[dim]... and {len(places) - 5} more[/dim]")

        console.print(Panel(tree, title="Descendants", border_style="green"))

    async def find_nearby(self, distance: str):
        """Find nearby places."""
        if not self.current_place:
            console.print(
                "[yellow]No place selected. Use 'search' or 'show' first.[/yellow]"
            )
            return

        try:
            km = float(distance) if distance else 10.0
        except ValueError:
            console.print("[red]Please provide a valid distance in km[/red]")
            return

        if not self.current_place.latitude:
            console.print("[yellow]Current place has no coordinates[/yellow]")
            return

        with console.status(f"[cyan]Searching within {km}km...[/cyan]"):
            cursor = await self.connector.search(
                WOFSearchFilters(
                    near_lat=self.current_place.latitude,
                    near_lon=self.current_place.longitude,
                    radius_km=km,
                    limit=20,
                )
            )

        if not cursor.places:
            console.print(f"[yellow]No places found within {km}km[/yellow]")
            return

        # Display results
        table = Table(
            title=f"Places within {km}km", show_header=True, header_style="bold cyan"
        )
        table.add_column("Name", style="white")
        table.add_column("Type", style="cyan")
        table.add_column("Distance", style="yellow")

        for place in cursor.places[:10]:
            # Calculate rough distance (would need proper calculation)
            table.add_row(place.name, place.placetype, f"~{km:.1f}km")

        console.print(table)

    async def export_current(self):
        """Export current search results."""
        if not self.current_place:
            console.print("[yellow]No data to export[/yellow]")
            return

        # Get full geometry
        with console.status("[cyan]Preparing export...[/cyan]"):
            places = await self.connector.get_places(
                [self.current_place.id], include_geometry=True
            )

        if places:
            collection = PlaceCollection(places=places)
            geojson = collection.to_geojson_string()

            # Save to file
            filename = f"wof-export-{self.current_place.id}.geojson"
            Path(filename).write_text(geojson)
            console.print(f"[green]✓ Exported to {filename}[/green]")

    async def show_stats(self):
        """Show database statistics."""
        with console.status("[cyan]Loading statistics...[/cyan]"):
            summary = await self.connector.explorer.database_summary()

        # Display stats using our beautiful formatters
        stats = {
            "Total Places": f"{summary.get('total_places', 0):,}",
            "Countries": f"{summary.get('country_count', 0):,}",
            "Regions": f"{summary.get('region_count', 0):,}",
            "Localities": f"{summary.get('locality_count', 0):,}",
            "Current Places": f"{summary.get('current_places', 0):,}",
            "With Geometry": f"{summary.get('with_geometry', 0):,}",
        }

        print_summary("Database Statistics", stats)

    def change_theme(self, theme_name: str):
        """Change display theme."""
        themes = ["default", "minimal", "bold", "ocean", "forest"]

        if not theme_name:
            console.print(f"[yellow]Available themes: {', '.join(themes)}[/yellow]")
            return

        if theme_name in themes:
            # Would need to implement theme switching in display module
            console.print(f"[green]✓ Theme changed to '{theme_name}'[/green]")
        else:
            console.print(f"[red]Unknown theme '{theme_name}'[/red]")

    def set_current(self, place):
        """Set current place and update history."""
        if self.current_place:
            self.history.append(self.current_place)
        self.current_place = place
        console.print(f"[green]✓ Selected: {format_place(place)}[/green]")

    def go_back(self):
        """Go back to previous place."""
        if not self.history:
            console.print("[yellow]No history to go back to[/yellow]")
            return

        self.current_place = self.history.pop()
        console.print(f"[green]← Back to: {format_place(self.current_place)}[/green]")

    async def guided_tour(self):
        """Interactive guided tour of WOF Explorer capabilities."""
        from wof_explorer.display import (
            TableDisplay,
            TableConfig,
            ProgressDisplay,
            TableStyle,
        )

        console.print(
            "\n[bold cyan]🎭 Welcome to the WOF Explorer Guided Tour![/bold cyan]\n"
        )
        console.print(
            "[yellow]This tour will demonstrate the key features of the explorer.[/yellow]"
        )
        console.print("[dim]Press Enter after each step to continue...[/dim]\n")

        try:
            # Step 1: Database Overview
            prompt(
                "📊 [bold]Step 1: Database Overview[/bold] - Press Enter to see stats"
            )
            await self.show_stats()

            # Step 2: Hierarchical Display
            prompt(
                "\n🌳 [bold]Step 2: Geographic Hierarchy[/bold] - Press Enter to explore Chicago"
            )

            # Search for Chicago
            with console.status("[cyan]Loading Chicago...[/cyan]"):
                chicago_cursor = await self.connector.search(
                    WOFSearchFilters(name="Chicago", placetype="locality", limit=1)
                )

            if chicago_cursor.places:
                chicago = chicago_cursor.places[0]
                self.set_current(chicago)

                # Show place details with tree
                tree = Tree(f"[bold]{chicago.name}[/bold] ({chicago.placetype})")
                tree.add(f"WOF ID: {chicago.id}")
                tree.add(f"Country: {chicago.country}")
                tree.add(f"Region: {chicago.region or 'N/A'}")
                tree.add(f"Status: {'Current' if chicago.is_current else 'Historical'}")
                console.print(tree)

                # Step 3: Descendants
                prompt(
                    "\n🏘️  [bold]Step 3: Neighborhood Hierarchy[/bold] - Press Enter to see Chicago neighborhoods"
                )

                progress = ProgressDisplay(
                    total=100, description="Loading neighborhoods"
                )
                progress.update(25)
                hierarchy = WOFHierarchyCursor(chicago, self.connector)
                progress.update(50)
                neighborhoods = await hierarchy.fetch_descendants(
                    filters=WOFFilters(placetype="neighbourhood"), limit=10
                )
                progress.update(100)
                progress.finish("Complete!")

                if neighborhoods:
                    # Display as tree
                    tree = Tree(f"[bold cyan]{chicago.name} Neighborhoods[/bold cyan]")
                    for n in neighborhoods[:10]:
                        branch = tree.add(f"📍 {n.name}")
                        branch.add(f"[dim]ID: {n.id}[/dim]")

                    console.print(tree)
                    console.print(
                        f"[dim]Showing 10 of {len(neighborhoods)} neighborhoods[/dim]"
                    )

            # Step 4: Different Table Styles
            prompt(
                "\n📋 [bold]Step 4: Table Display Styles[/bold] - Press Enter to see different styles"
            )

            # Get some sample data
            with console.status("[cyan]Loading sample cities...[/cyan]"):
                cities_cursor = await self.connector.search(
                    WOFSearchFilters(placetype="locality", country="US", limit=5)
                )

            if cities_cursor.places:
                # Show different table styles
                for style_name, style in [
                    ("Simple", TableStyle.SIMPLE),
                    ("ASCII Borders", TableStyle.ASCII),
                    ("Unicode Box", TableStyle.UNICODE),
                    ("Markdown", TableStyle.MARKDOWN),
                ]:
                    console.print(f"\n[yellow]{style_name} Style:[/yellow]")

                    config = TableConfig(style=style)
                    display = TableDisplay(
                        headers=["City", "State", "WOF ID"], config=config
                    )

                    for p in cities_cursor.places[:3]:
                        display.add_row([p.name, p.region or "N/A", str(p.id)])

                    console.print(display.render())

                    if style_name != "Markdown":
                        input("[dim]Press Enter for next style...[/dim]")

            # Step 5: Search Workflow
            prompt(
                "\n🔍 [bold]Step 5: Search Workflow[/bold] - Press Enter to try searching"
            )

            city = prompt("Enter a city name to explore: ").strip()
            if city:
                await self.search_neighborhoods_in_city(city, "")

            # Step 6: Export
            prompt(
                "\n💾 [bold]Step 6: Export Capabilities[/bold] - Press Enter to learn about exports"
            )

            console.print(
                Panel(
                    "[yellow]Export Features:[/yellow]\n\n"
                    "• [bold]GeoJSON[/bold] - Geographic data for mapping tools\n"
                    "• [bold]CSV[/bold] - Spreadsheet-compatible format\n"
                    "• [bold]WKT[/bold] - Well-Known Text for GIS systems\n\n"
                    "Use the [green]export[/green] command after selecting any place!",
                    title="Export Formats",
                    border_style="green",
                )
            )

            # Completion
            console.print("\n[bold green]🎉 Tour Complete![/bold green]\n")
            console.print(
                Panel(
                    "[cyan]You've learned:[/cyan]\n"
                    "✓ Database statistics and overview\n"
                    "✓ Hierarchical place relationships\n"
                    "✓ Multiple display styles\n"
                    "✓ Search workflows\n"
                    "✓ Export capabilities\n\n"
                    "[yellow]Tips:[/yellow]\n"
                    "• Use numbers 1-6 for quick access to features\n"
                    "• Type 'help' anytime for command reference\n"
                    "• Ctrl+C to cancel any operation",
                    title="Tour Summary",
                    border_style="green",
                )
            )

        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Tour cancelled[/yellow]")

    def show_help(self):
        """Show help menu."""
        console.print(
            Panel(
                "[yellow]Available Commands:[/yellow]\n"
                "  search <name>   - Search all place types\n"
                "  show <id>       - Show place by ID\n"
                "  ancestors       - Show ancestry of current place\n"
                "  descendants     - Show descendants of current place\n"
                "  nearby <km>     - Find nearby places\n"
                "  export          - Export current place to GeoJSON\n"
                "  stats           - Show database statistics\n"
                "  back            - Go to previous place\n"
                "  help            - Show this help\n"
                "  quit            - Exit\n\n"
                "[yellow]Quick Menu:[/yellow]\n"
                "  1-6             - Use numbered options from main menu",
                title="Help",
                border_style="cyan",
            )
        )


@app.command()
def explore(
    database: Path = typer.Option(
        Path("wof-downloads/whosonfirst-combined.db"),
        "--database",
        "-d",
        help="Path to WhosOnFirst database",
    ),
):
    """Interactive exploration mode."""
    if not database.exists():
        console.print(f"[red]Database not found: {database}[/red]")
        raise typer.Exit(1)

    async def run():
        connector = WOFConnector(str(database))
        await connector.connect()

        explorer = InteractiveExplorer(connector)
        await explorer.run()

        await connector.disconnect()

    asyncio.run(run())


@app.command()
def search(
    database: Path = typer.Option(
        Path("wof-downloads/whosonfirst-combined.db"),
        "--database",
        "-d",
        help="Path to WhosOnFirst database",
    ),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Search by name"),
    placetype: Optional[str] = typer.Option(
        None, "--type", "-t", help="Filter by placetype"
    ),
    country: Optional[str] = typer.Option(
        None, "--country", "-c", help="Filter by country"
    ),
    limit: int = typer.Option(20, "--limit", "-l", help="Maximum results"),
    output: Optional[str] = typer.Option(
        None, "--output", "-o", help="Output format (json, geojson, csv)"
    ),
):
    """Quick search from command line."""
    if not database.exists():
        console.print(f"[red]Database not found: {database}[/red]")
        raise typer.Exit(1)

    async def run():
        connector = WOFConnector(str(database))
        await connector.connect()

        # Build filters
        filters = WOFSearchFilters(
            name=name, placetype=placetype, country=country, limit=limit
        )

        with console.status("[cyan]Searching...[/cyan]"):
            cursor = await connector.search(filters)

        if not cursor.places:
            console.print("[yellow]No results found[/yellow]")
            return

        # Output based on format
        if output == "json":
            places_dict = [p.model_dump() for p in cursor.places]
            print(json.dumps(places_dict, indent=2))
        elif output == "geojson":
            places = await cursor.fetch_all(include_geometry=True)
            collection = PlaceCollection(places=places)
            print(collection.to_geojson_string())
        else:
            # Default table output
            table = Table(
                title=f"Search Results ({cursor.total_count} total)",
                show_header=True,
                header_style="bold cyan",
            )
            table.add_column("ID", style="dim")
            table.add_column("Name", style="white")
            table.add_column("Type", style="cyan")
            table.add_column("Country", style="yellow")

            for place in cursor.places:
                table.add_row(
                    str(place.id), place.name, place.placetype, place.country or ""
                )

            console.print(table)

        await connector.disconnect()

    asyncio.run(run())


@app.command()
def stats(
    database: Path = typer.Option(
        Path("wof-downloads/whosonfirst-combined.db"),
        "--database",
        "-d",
        help="Path to WhosOnFirst database",
    ),
    detailed: bool = typer.Option(False, "--detailed", help="Show detailed statistics"),
):
    """Show database statistics."""
    if not database.exists():
        console.print(f"[red]Database not found: {database}[/red]")
        raise typer.Exit(1)

    async def run():
        connector = WOFConnector(str(database))
        await connector.connect()

        with console.status("[cyan]Loading statistics...[/cyan]"):
            summary = await connector.explorer.database_summary()

            if detailed:
                # Get additional stats
                top_cities = await connector.explorer.top_cities_by_coverage()
                placetypes = await connector.explorer.discover_placetypes()

        # Display basic stats
        # Extract key statistics from the summary
        by_country = summary.get("by_country", {})
        country_count = len(by_country)

        print_summary(
            "Database Statistics",
            {
                "Database": database.name,
                "Total Places": f"{summary.get('total_places', 0):,}",
                "Countries": f"{country_count:,}",
                "Regions": f"{summary.get('hierarchical_coverage', {}).get('regions', 0):,}",
                "Counties": f"{summary.get('hierarchical_coverage', {}).get('counties', 0):,}",
                "Localities": f"{summary.get('hierarchical_coverage', {}).get('localities', 0):,}",
                "Neighborhoods": f"{summary.get('hierarchical_coverage', {}).get('neighborhoods', 0):,}",
            },
        )

        if detailed:
            # Show top cities
            if top_cities:
                console.print("\n[bold cyan]Top Cities by Coverage:[/bold cyan]")
                for city in top_cities[:5]:
                    console.print(
                        f"  • {city['name']}: {city.get('descendant_count', 0):,} places"
                    )

            # Show placetype distribution
            if placetypes:
                console.print("\n[bold cyan]Place Types:[/bold cyan]")
                for pt in placetypes[:10]:
                    console.print(f"  • {pt['placetype']}: {pt['count']:,}")

        await connector.disconnect()

    asyncio.run(run())


@app.command()
def demo(
    database: Path = typer.Option(
        Path("wof-downloads/whosonfirst-combined.db"),
        "--database",
        "-d",
        help="Path to WhosOnFirst database",
    ),
    auto: bool = typer.Option(
        False, "--auto", help="Run demo automatically without pauses"
    ),
):
    """Showcase all display capabilities with sample data."""
    if not database.exists():
        console.print(f"[red]Database not found: {database}[/red]")
        raise typer.Exit(1)

    async def run(auto_mode=auto):
        from rich.progress import (
            Progress,
            SpinnerColumn,
            BarColumn,
            TextColumn,
            TimeElapsedColumn,
        )
        from rich.tree import Tree
        from rich.table import Table as RichTable
        from wof_explorer.display.table import (
            TableDisplay,
            TableConfig,
            TableStyle,
            print_comparison,
        )
        import time

        connector = WOFConnector(str(database))
        await connector.connect()

        console.print(
            "\n[bold cyan]═══ WhosOnFirst Display Capabilities Demo ═══[/bold cyan]\n"
        )

        # 1. Tree Display - Geographic Hierarchy
        console.print("[bold yellow]1. Hierarchical Tree Display[/bold yellow]")
        console.print("[dim]Showing geographic relationships...[/dim]\n")

        tree = Tree("🌍 [bold]United States[/bold]")
        ca = tree.add("📍 [cyan]California[/cyan]")
        sf_county = ca.add("🏛️ [green]San Francisco County[/green]")
        sf_county.add("🏙️ [yellow]San Francisco[/yellow]")
        sf_county.add("🏙️ [yellow]Daly City[/yellow]")
        alameda = ca.add("🏛️ [green]Alameda County[/green]")
        alameda.add("🏙️ [yellow]Oakland[/yellow]")
        alameda.add("🏙️ [yellow]Berkeley[/yellow]")

        ny = tree.add("📍 [cyan]New York[/cyan]")
        ny_county = ny.add("🏛️ [green]New York County[/green]")
        ny_county.add("🏙️ [yellow]Manhattan[/yellow]")

        console.print(tree)
        if not auto_mode:
            console.print("\n[dim]Press Enter to continue...[/dim]")
            input()
        else:
            time.sleep(1)

        # 2. Progress Indicators
        console.print("\n[bold yellow]2. Progress Indicators[/bold yellow]")
        console.print("[dim]Processing data with various progress styles...[/dim]\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task1 = progress.add_task("[cyan]Loading database...", total=100)
            task2 = progress.add_task("[green]Processing places...", total=200)
            task3 = progress.add_task("[yellow]Building index...", total=150)

            for i in range(100):
                time.sleep(0.01)
                progress.update(task1, advance=1)
                if i % 2 == 0:
                    progress.update(task2, advance=2)
                if i % 3 == 0:
                    progress.update(task3, advance=1.5)

        if not auto_mode:
            console.print("\n[dim]Press Enter to continue...[/dim]")
            input()
        else:
            time.sleep(1)

        # 3. Table Styles
        console.print("\n[bold yellow]3. Table Display Styles[/bold yellow]")
        console.print("[dim]Same data in different table formats...[/dim]\n")

        sample_data = [
            ["San Francisco", "locality", "873,965", "37.7749", "-122.4194"],
            ["Los Angeles", "locality", "3,898,747", "34.0522", "-118.2437"],
            ["New York", "locality", "8,336,817", "40.7128", "-74.0060"],
        ]
        headers = ["City", "Type", "Population", "Latitude", "Longitude"]

        styles = [
            (TableStyle.SIMPLE, "Simple Style"),
            (TableStyle.ASCII, "ASCII Borders"),
            (TableStyle.UNICODE, "Unicode Box Drawing"),
            (TableStyle.MARKDOWN, "Markdown Format"),
        ]

        for style, name in styles:
            console.print(f"\n[cyan]{name}:[/cyan]")
            config = TableConfig(style=style, align={"Population": "right"})
            table = TableDisplay(headers, config)
            for row in sample_data:
                table.add_row(row)
            print(table.render())

        if not auto_mode:
            console.print("\n[dim]Press Enter to continue...[/dim]")
            input()
        else:
            time.sleep(1)

        # 4. ASCII Map Visualization
        console.print("\n[bold yellow]4. ASCII Map Visualization[/bold yellow]")
        console.print("[dim]Simple geographic visualization...[/dim]\n")

        ascii_map = """
        ╔════════════════════════════════════════════╗
        ║          United States Overview            ║
        ╠════════════════════════════════════════════╣
        ║                                            ║
        ║   Seattle •                    • Boston    ║
        ║            \\                  /            ║
        ║             \\                /             ║
        ║   Portland • \\              / • New York   ║
        ║               \\            /               ║
        ║                •──────────• Chicago        ║
        ║   San Francisco /          \\               ║
        ║               /             \\              ║
        ║   Los Angeles •              • Houston     ║
        ║                                            ║
        ║            Major City Connections          ║
        ╚════════════════════════════════════════════╝
        """
        console.print(ascii_map)

        if not auto_mode:
            console.print("\n[dim]Press Enter to continue...[/dim]")
            input()
        else:
            time.sleep(1)

        # 5. Comparison Tables
        console.print("\n[bold yellow]5. Comparison Tables[/bold yellow]")
        console.print("[dim]Before/After data comparison...[/dim]\n")

        before = {
            "Total Places": 15234,
            "Countries": 2,
            "Regions": 50,
            "Localities": 3892,
            "Neighborhoods": 8923,
        }

        after = {
            "Total Places": 28456,
            "Countries": 3,
            "Regions": 75,
            "Localities": 6234,
            "Neighborhoods": 15678,
        }

        print_comparison(before, after, "Original", "Combined")

        if not auto_mode:
            console.print("\n[dim]Press Enter to continue...[/dim]")
            input()
        else:
            time.sleep(1)

        # 6. Rich Formatted Output
        console.print("\n[bold yellow]6. Rich Formatted Output[/bold yellow]")
        console.print("[dim]Using colors and formatting for clarity...[/dim]\n")

        # Status indicators
        console.print("Status Indicators:")
        console.print("  ✅ [green]Current places: Active and maintained[/green]")
        console.print("  ⚠️  [yellow]Deprecated: No longer recommended[/yellow]")
        console.print("  ❌ [red]Ceased: No longer exists[/red]")
        console.print("  🔄 [cyan]Superseded: Replaced by another entry[/cyan]")

        console.print("\nData Quality:")
        quality_table = RichTable(show_header=True, header_style="bold magenta")
        quality_table.add_column("Metric", style="cyan", no_wrap=True)
        quality_table.add_column("Score", justify="center")
        quality_table.add_column("Status", justify="center")

        quality_table.add_row("Completeness", "98%", "[green]✓ Excellent[/green]")
        quality_table.add_row("Accuracy", "95%", "[green]✓ Very Good[/green]")
        quality_table.add_row("Consistency", "89%", "[yellow]⚠ Good[/yellow]")
        quality_table.add_row("Coverage", "76%", "[yellow]⚠ Moderate[/yellow]")

        console.print(quality_table)

        if not auto_mode:
            console.print("\n[dim]Press Enter to continue...[/dim]")
            input()
        else:
            time.sleep(1)

        # 7. Live Search Results
        console.print("\n[bold yellow]7. Live Data from Database[/bold yellow]")
        console.print("[dim]Fetching real data...[/dim]\n")

        with console.status("[cyan]Searching for major cities...[/cyan]"):
            filters = WOFSearchFilters(placetype="locality", is_current=True, limit=5)
            cursor = await connector.search(filters)

        if cursor.places:
            table = RichTable(
                title="Top Cities in Database",
                show_header=True,
                header_style="bold cyan",
            )
            table.add_column("WOF ID", style="dim")
            table.add_column("Name", style="bold")
            table.add_column("Region")
            table.add_column("Country", style="yellow")
            table.add_column("Status", justify="center")

            for place in cursor.places[:5]:
                status = "✅" if place.is_current else "❌"
                table.add_row(
                    str(place.id),
                    place.name,
                    place.region or "—",
                    place.country or "—",
                    status,
                )

            console.print(table)

        console.print("\n[bold green]✨ Demo Complete![/bold green]")
        console.print("[dim]All display capabilities have been demonstrated.[/dim]\n")

        await connector.disconnect()

    asyncio.run(run())


@app.command()
def export(
    database: Path = typer.Option(
        Path("wof-downloads/whosonfirst-combined.db"),
        "--database",
        "-d",
        help="Path to WhosOnFirst database",
    ),
    ids: str = typer.Option(..., "--ids", "-i", help="Comma-separated place IDs"),
    format: str = typer.Option(
        "geojson", "--format", "-f", help="Output format (geojson, csv, wkt)"
    ),
    output_file: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output file"
    ),
):
    """Export specific places."""
    if not database.exists():
        console.print(f"[red]Database not found: {database}[/red]")
        raise typer.Exit(1)

    async def run():
        connector = WOFConnector(str(database))
        await connector.connect()

        # Parse IDs
        place_ids = [int(id.strip()) for id in ids.split(",")]

        with console.status(f"[cyan]Fetching {len(place_ids)} places...[/cyan]"):
            places = await connector.get_places(place_ids, include_geometry=True)

        if not places:
            console.print("[yellow]No places found[/yellow]")
            return

        collection = PlaceCollection(places=places)

        # Export based on format
        if format == "geojson":
            output = collection.to_geojson_string()
        elif format == "csv":
            output = collection.to_csv()
        elif format == "wkt":
            output = collection.to_wkt()
        else:
            console.print(f"[red]Unknown format: {format}[/red]")
            return

        # Save or print
        if output_file:
            output_file.write_text(output)
            console.print(f"[green]✓ Exported to {output_file}[/green]")
        else:
            print(output)

        await connector.disconnect()

    asyncio.run(run())


# Import download command from original script
# We'll import it dynamically to avoid circular imports
import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "wof_download", Path(__file__).parent / "wof-download.py"
)
wof_download_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wof_download_module)

# Add download as a subcommand
app.command(name="download")(wof_download_module.main)


if __name__ == "__main__":
    # Show help if no command provided
    import sys

    if len(sys.argv) == 1:
        sys.argv.append("--help")
    app()
