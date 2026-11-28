/** @odoo-module **/

import {Component, onWillStart, useState} from "@odoo/owl";
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";
import {_t} from "@web/core/l10n/translation";

/**
 * Figures of the social accounts, drawn from the daily rows of
 * ``social.account.statistics`` and from the publications themselves.
 *
 * The screen only formats what the server aggregated: every number, label
 * and post comes from the database.
 */
export class SocialStatisticsDashboard extends Component {
    static template = "social_media_base.StatisticsDashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            period: 30,
            accountId: false,
            loading: true,
            error: "",
            data: null,
            charts: {},
        });
        onWillStart(() => this.load());
    }

    async load() {
        this.state.loading = true;
        this.state.error = "";
        try {
            this.state.data = await this.orm.call(
                "social.account.statistics",
                "get_dashboard_data",
                [this.state.period, this.state.accountId]
            );
            this.buildCharts();
        } catch (error) {
            this.state.data = null;
            this.state.error = this.errorMessage(error);
        } finally {
            this.state.loading = false;
        }
    }

    errorMessage(error) {
        return (
            (error && error.data && error.data.message) ||
            (error && error.message) ||
            _t("The statistics could not be read.")
        );
    }

    retry() {
        this.load();
    }

    async setPeriod(period) {
        if (this.state.period === period) {
            return;
        }
        this.state.period = period;
        await this.load();
    }

    async setAccount(ev) {
        this.state.accountId = ev.target.value ? Number(ev.target.value) : false;
        await this.load();
    }

    openDetailed() {
        if (this.state.data) {
            this.action.doAction(this.state.data.detailed_action_id);
        }
    }

    get kpis() {
        return this.state.data?.kpis ?? {};
    }

    get topPosts() {
        return this.state.data?.top_posts ?? [];
    }

    get byAccount() {
        return this.state.data?.by_account ?? [];
    }

    get accounts() {
        return this.state.data?.accounts ?? [];
    }

    /**
     * Turn a series into the coordinates the SVG draws.
     *
     * The maximum is rounded up so the line never touches the top border,
     * and the labels are thinned out to the six that fit on the axis.
     *
     * @param {number[]} values one value per day of the period
     * @param {String} kind ``number`` or ``percent``, only for the labels
     */
    buildChart(values, kind) {
        const max = Math.max(1, ...values);
        const width = 640;
        const height = 220;
        const pad = 36;
        const step = values.length > 1 ? (width - pad * 2) / (values.length - 1) : 0;
        const points = values.map((value, index) => [
            pad + index * step,
            height - pad - (value / max) * (height - pad * 2),
        ]);
        const line = points
            .map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`)
            .join(" ");
        const area = `${pad},${height - pad} ${line} ${(
            pad +
            (values.length - 1) * step
        ).toFixed(1)},${height - pad}`;
        const series = this.state.data?.series ?? [];
        const every = Math.max(1, Math.ceil(series.length / 6));
        const labels = series
            .map((item, index) => ({
                index,
                label: item.date.slice(5),
                x: pad + index * step,
            }))
            .filter((item) => item.index % every === 0);
        const ticks = [0, 0.5, 1].map((ratio) => ({
            y: height - pad - ratio * (height - pad * 2),
            value: max * ratio,
        }));
        return {line, area, labels, ticks, width, height, pad, kind};
    }

    buildCharts() {
        const series = this.state.data?.series ?? [];
        this.state.charts = {
            impressions: this.buildChart(
                series.map((item) => item.impressions),
                "number"
            ),
            engagement: this.buildChart(
                series.map((item) => item.engagement),
                "percent"
            ),
        };
    }

    formatNumber(value) {
        return new Intl.NumberFormat(undefined, {maximumFractionDigits: 0}).format(
            value || 0
        );
    }

    formatPercent(value) {
        return `${(value || 0).toFixed(2)} %`;
    }

    formatAxis(value, kind) {
        if (kind === "percent") {
            return `${(value || 0).toFixed(1)} %`;
        }
        return new Intl.NumberFormat(undefined, {maximumFractionDigits: 1}).format(
            value || 0
        );
    }

    formatDate(value) {
        return value ? value.slice(0, 10) : "";
    }
}

registry
    .category("actions")
    .add("social_statistics_dashboard", SocialStatisticsDashboard);
