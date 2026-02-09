"""Tests for Recommendations improvements."""

import pytest
from concordcore.core.recommendation import (
    RecommendationActionType,
    RecommendationAction,
    RecommendationVar,
    EvaluatedRecommendation,
)


class TestRecommendationActionType:
    def test_all_action_types_exist(self):
        assert RecommendationActionType.prescribe == 'prescribe'
        assert RecommendationActionType.order_test == 'order-test'
        assert RecommendationActionType.schedule_screening == 'schedule-screening'
        assert RecommendationActionType.counseling == 'counseling'
        assert RecommendationActionType.referral == 'referral'
        assert RecommendationActionType.lifestyle_modification == 'lifestyle-modification'
        assert RecommendationActionType.monitoring == 'monitoring'


class TestRecommendationAction:
    def test_all_actions_exist(self):
        assert RecommendationAction.pending == 'pending'
        assert RecommendationAction.accepted == 'accepted'
        assert RecommendationAction.rejected == 'rejected'
        assert RecommendationAction.deferred == 'deferred'
        assert RecommendationAction.not_applicable == 'not-applicable'


class TestEvaluatedRecommendation:
    def test_non_compliance_evidence_default_none(self):
        rec_var = RecommendationVar(id='test_rec', title='Test Rec')
        eval_rec = EvaluatedRecommendation(recommendation=rec_var)
        assert eval_rec.non_compliance_evidence is None

    def test_non_compliance_evidence_can_be_set(self):
        rec_var = RecommendationVar(id='test_rec', title='Test Rec')
        eval_rec = EvaluatedRecommendation(recommendation=rec_var)
        eval_rec.non_compliance_evidence = []
        assert eval_rec.non_compliance_evidence == []


class TestConcordUserRecommendationActions:
    def test_record_recommendation_action(self):
        from concordcore.core.concord_user import ConcordUser
        user = ConcordUser(user_id='p1')
        user.record_recommendation_action('statin_rec', 'accepted', reason='Patient agreed')
        assert len(user.recommendation_actions) == 1
        action = user.recommendation_actions[0]
        assert action['recommendation_id'] == 'statin_rec'
        assert action['action'] == 'accepted'
        assert action['reason'] == 'Patient agreed'

    def test_record_invalid_action_raises(self):
        from concordcore.core.concord_user import ConcordUser
        user = ConcordUser(user_id='p1')
        with pytest.raises(ValueError):
            user.record_recommendation_action('rec1', 'invalid-action')

    def test_multiple_actions(self):
        from concordcore.core.concord_user import ConcordUser
        user = ConcordUser(user_id='p1')
        user.record_recommendation_action('rec1', 'accepted')
        user.record_recommendation_action('rec2', 'deferred', reason='Need more info')
        user.record_recommendation_action('rec3', 'rejected', reason='Contraindicated')
        assert len(user.recommendation_actions) == 3

    def test_actions_serialized(self):
        from concordcore.core.concord_user import ConcordUser
        user = ConcordUser(user_id='p1')
        user.record_recommendation_action('rec1', 'accepted')
        d = user.to_dict()
        assert len(d['recommendation_actions']) == 1

    def test_actions_cleared(self):
        from concordcore.core.concord_user import ConcordUser
        user = ConcordUser(user_id='p1')
        user.record_recommendation_action('rec1', 'accepted')
        user.clear()
        assert len(user.recommendation_actions) == 0
