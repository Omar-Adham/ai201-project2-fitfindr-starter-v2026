"""Milestone 5 branch/state checks. No network or model calls.

Run: python -m unittest test_agent -v
"""

import unittest
from unittest.mock import patch

import agent
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe


class AgentTests(unittest.TestCase):
    def test_matching_run_preserves_session_values_at_tool_boundaries(self):
        original_new_session = agent.new_session
        captured = {}

        def start(query, wardrobe):
            captured['session'] = original_new_session(query, wardrobe)
            return captured['session']

        def outfit(item, wardrobe):
            session = captured['session']
            self.assertIs(item, session['selected_item'])
            self.assertIs(item, session['search_results'][0])
            self.assertIs(wardrobe, session['wardrobe'])
            self.assertIsNone(session['fit_card'])
            return 'Test outfit'

        def card(suggestion, item, wardrobe):
            session = captured['session']
            self.assertEqual(suggestion, session['outfit_suggestion'])
            self.assertEqual(suggestion, 'Test outfit')
            self.assertIs(item, session['selected_item'])
            self.assertIs(wardrobe, session['wardrobe'])
            return 'Test caption'

        with patch.object(agent, 'new_session', side_effect=start), \
             patch.object(agent, 'suggest_outfit', side_effect=outfit) as suggest, \
             patch.object(agent, 'create_fit_card', side_effect=card) as create:
            session = agent.run_agent('vintage graphic tee under $30', get_example_wardrobe())
        suggest.assert_called_once()
        create.assert_called_once()
        self.assertEqual(session['selected_item']['id'], 'lst_002')
        self.assertEqual(session['fit_card'], 'Test caption')
        self.assertIsNone(session['error'])

    def test_impossible_query_stops_before_model_tools_five_times(self):
        with patch.object(agent, 'suggest_outfit') as suggest, \
             patch.object(agent, 'create_fit_card') as create:
            for _ in range(5):
                session = agent.run_agent('designer ballgown size XXS under $5', get_example_wardrobe())
                self.assertEqual(session['search_results'], [])
                for field in ('selected_item', 'outfit_suggestion', 'fit_card'):
                    self.assertIsNone(session[field])
                self.assertIn('try different words', session['error'])
        suggest.assert_not_called()
        create.assert_not_called()

    def test_empty_wardrobe_reaches_both_tools(self):
        wardrobe = get_empty_wardrobe()
        with patch.object(agent, 'suggest_outfit', return_value='General advice') as suggest, \
             patch.object(agent, 'create_fit_card', return_value='Test caption') as create:
            session = agent.run_agent('denim jacket under $50', wardrobe)
        self.assertIs(suggest.call_args.args[1], wardrobe)
        create.assert_called_once_with('General advice', session['selected_item'], wardrobe)
        self.assertIsNone(session['error'])

    def test_shoe_sizes_and_decimal_prices(self):
        for spelling in ('size 8', 'size US 8', 'US8', 'US 8'):
            with self.subTest(spelling=spelling):
                parsed = agent.parse_query(f'platform sneakers {spelling} under $48.50')
                self.assertEqual(parsed, {'description': 'platform sneakers', 'size': 'US 8', 'max_price': 48.5})

    def test_price_only_failure_has_actionable_message(self):
        session = agent.run_agent('platform sneakers size 8 under $10', get_empty_wardrobe())
        self.assertIn('raise your $10 limit', session['error'])
        self.assertIsNone(session['fit_card'])


if __name__ == '__main__':
    unittest.main()
