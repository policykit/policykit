from django.shortcuts import render
from django_filters.views import FilterView
from django_filters import FilterSet
import django_tables2 as tables

from django_db_logger.models import EvaluationLog

class LogTable(tables.Table):
    create_datetime = tables.DateTimeColumn(format="Y-m-d\TH:m:s")
    action = tables.Column(accessor='action')
    policy = tables.Column(accessor='policy')

    class Meta:
        model = EvaluationLog
        template_name = "django_tables2/bootstrap.html"
        fields = ("create_datetime", "level", "action", "policy", "msg")


class CommunityLogFilter(FilterSet):
    class Meta:
        model = EvaluationLog
        fields = ("create_datetime", "level", "msg")

    @property
    def qs(self):
        parent = super(CommunityLogFilter, self).qs
        user = getattr(self.request, "user", None)
        if user and hasattr(user, "community"):
            return parent.filter(community=user.community.community)
        return parent.none()


class LogListView(tables.SingleTableMixin, FilterView):
    model = EvaluationLog
    table_class = LogTable
    template_name = "policyadmin/dashboard/logs.html"
    paginator_class = tables.LazyPaginator

    filterset_class = CommunityLogFilter
