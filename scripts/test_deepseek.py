"""
Test DeepSeek API connection and basic functionality.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ai.deepseek_client import DeepSeekClient


async def test_deepseek():
    """Test DeepSeek API connection."""
    print("🧪 Testing DeepSeek API Connection...\n")

    # Get API key from environment
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("❌ DEEPSEEK_API_KEY not found in environment")
        print("   Set it in .env file or export DEEPSEEK_API_KEY=your_key")
        return False

    use_netmind = os.getenv("DEEPSEEK_USE_NETMIND", "true").lower() == "true"
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    print(f"📋 Configuration:")
    print(f"   API Key: {api_key[:10]}...{api_key[-4:]}")
    print(f"   Use NetMind: {use_netmind}")
    print(f"   Model: {model}\n")

    # Initialize client
    client = DeepSeekClient(
        api_key=api_key,
        model=model,
        use_netmind=use_netmind
    )

    try:
        await client.init()
        print("✅ Client initialized successfully\n")

        # Test simple request
        print("🔄 Testing simple market analysis request...")

        analysis = await client.analyze_market(
            symbol="SOL",
            current_price=100.50,
            order_book_data={
                'imbalance': 0.65,
                'bid_liquidity': 50000,
                'ask_liquidity': 30000,
                'spread_bps': 25
            },
            nansen_data={
                'action': 'BUY',
                'confidence': 0.85,
                'score': 0.6,
                'signals': [
                    {
                        'type': 'smart_money_flow',
                        'strength': 'strong_buy',
                        'confidence': 0.9,
                        'reasoning': 'Top 100 wallets accumulating'
                    }
                ]
            },
            market_context="Testing DeepSeek integration"
        )

        print("\n✅ Analysis received!")
        print(f"\n📊 DeepSeek Analysis:")
        print(f"   Symbol: {analysis.symbol}")
        print(f"   Action: {analysis.action}")
        print(f"   Confidence: {analysis.confidence:.2%}")
        print(f"   Risk/Reward: {analysis.risk_reward_ratio:.1f}:1" if analysis.risk_reward_ratio else "   Risk/Reward: Not specified")
        print(f"   Entry: ${analysis.entry_price:.2f}" if analysis.entry_price else "   Entry: Not specified")
        print(f"   Stop Loss: ${analysis.stop_loss:.2f}" if analysis.stop_loss else "   Stop Loss: Not specified")
        print(f"   Take Profit: ${analysis.take_profit:.2f}" if analysis.take_profit else "   Take Profit: Not specified")
        print(f"   Hold Duration: {analysis.hold_duration_hours}h" if analysis.hold_duration_hours else "   Hold Duration: Not specified")
        print(f"\n💡 Reasoning:\n   {analysis.reasoning}\n")

        # Check if meets Alpha Arena criteria
        print("🏆 Alpha Arena Criteria Check:")
        meets_confidence = analysis.confidence >= 0.7
        meets_rr = analysis.risk_reward_ratio and analysis.risk_reward_ratio >= 6.0

        print(f"   {'✅' if meets_confidence else '❌'} Confidence ≥ 0.7: {analysis.confidence:.2%}")
        print(f"   {'✅' if meets_rr else '❌'} Risk/Reward ≥ 6:1: {analysis.risk_reward_ratio:.1f}:1" if analysis.risk_reward_ratio else f"   ❌ Risk/Reward ≥ 6:1: Not calculated")

        if meets_confidence and meets_rr:
            print("\n🎉 This would be a VALID trade according to DeepSeek Alpha Arena criteria!")
        else:
            print("\n⚠️  This would be REJECTED (doesn't meet Alpha Arena criteria)")

        await client.close()
        print("\n✅ All tests passed! DeepSeek is ready to trade.\n")
        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print(f"   Type: {type(e).__name__}")
        print(f"\n🔍 Troubleshooting:")
        print(f"   1. Check your API key is correct")
        print(f"   2. Verify NetMind.ai account has credits")
        print(f"   3. Try setting DEEPSEEK_USE_NETMIND=false for direct API")
        print(f"   4. Check internet connection\n")
        return False


if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()

    result = asyncio.run(test_deepseek())
    sys.exit(0 if result else 1)
