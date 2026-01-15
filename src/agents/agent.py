import asyncio

from src.agents.user_agent import agent

async def main():
    t = agent.get_new_thread()
    r = await agent.run("I love blue", thread=t)
    r = await agent.run("I quite like red too", thread=t)
    r = await agent.run("What did I buy?", thread=t)
    r = await agent.run("I really like the bikini I got", thread=t)
    r = await agent.run("actually, i don't really like red", thread=t)

if __name__ == "__main__":
    asyncio.run(main())