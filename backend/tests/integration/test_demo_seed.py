"""The demo dataset is built through the services: keep it working as they evolve."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import FixedClock
from app.core.config import Settings
from app.db.demo import DEMO_EMAIL, DEMO_PASSWORD, DemoSeeder
from tests.helpers import API, data, login


async def test_demo_seed_is_idempotent_and_usable(
    client: AsyncClient, db_session: AsyncSession, settings: Settings, clock: FixedClock
) -> None:
    seeder = DemoSeeder(db_session, settings, clock)
    assert await seeder.run() is True
    assert await DemoSeeder(db_session, settings, clock).run() is False

    demo = await login(client, DEMO_EMAIL, DEMO_PASSWORD)
    dashboard = data(await client.get(f"{API}/dashboard", headers=demo.headers))
    assert dashboard["totals"]["vehicles"] == 2
    assert dashboard["totals"]["open_alerts"] > 0
    logan = next(v for v in dashboard["vehicles"] if v["vehicle"]["display_name"] == "Family Logan")
    timeline = (
        await client.get(f"{API}/vehicles/{logan['vehicle']['id']}/timeline", headers=demo.headers)
    ).json()
    assert timeline["meta"]["total"] > 20
