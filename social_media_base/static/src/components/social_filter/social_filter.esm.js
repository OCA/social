import {Component, useRef, useState} from "@odoo/owl";
import {DateTimePicker} from "@web/core/datetime/datetime_picker";
import {DateTimePickerPopover} from "@web/core/datetime/datetime_picker_popover";
import {Dropdown} from "@web/core/dropdown/dropdown";
import {DropdownItem} from "@web/core/dropdown/dropdown_item";

const {DateTime} = luxon;

export class SocialFilter extends Component {
    static template = "social_media_base.SocialFilter";
    static props = {
        startDate: {type: String, optional: true},
        endDate: {type: String, optional: true},
        posts: {type: Array, optional: true},
        objectId: {type: Number, optional: true},
        campaigns: {type: Array, optional: true},
        clearFilter: {type: Function, optional: true},
        searchEnable: {type: Boolean, optional: true, default: false},
        filter: {type: Function, required: true},
        filterGranularity: {type: Boolean, optional: true, default: false},
    };
    static components = {
        Dropdown,
        DropdownItem,
        DateTimePicker,
        DateTimePickerPopover,
    };

    /**
     * Setups the component by storing the references of the different HTML
     * elements of the filter panel and by setting the state of the component.
     */
    setup() {
        super.setup();
        this.startDate = "";
        this.endDate = "";
        this.inputSearch = useRef("inputSearch");
        this.state = useState({
            loadFilter: false,
            currentFilterType: {id: "week", name: "Week"},
            currentStartDate: DateTime.now().minus({months: 1}).toFormat("dd/MM/yyyy"),
            currentEndDate: DateTime.now().toFormat("dd/MM/yyyy"),
            showStartDate: false,
            showEndDate: false,
        });
    }

    get filter_types() {
        return [
            {id: "day", name: "Day"},
            {id: "week", name: "Week"},
            {id: "month", name: "Month"},
        ];
    }

    async onSelectTypeRange(type_range) {
        this.state.currentFilterType = type_range;
        await this.onFilter();
    }

    onSelectShowDate(typeDate) {
        if (typeDate === "start") {
            this.state.showStartDate = true;
            this.state.showEndDate = false;
        } else if (typeDate === "end") {
            this.state.showEndDate = true;
            this.state.showStartDate = false;
        }
    }

    async onSelectStartDate(val_date) {
        this.state.currentStartDate = val_date.toFormat("dd/MM/yyyy");
        this.state.showStartDate = false;
        if (this.state.currentStartDate) await this.onFilter();
    }

    async onSelectEndDate(val_date) {
        this.state.currentEndDate = val_date.toFormat("dd/MM/yyyy");
        this.state.showEndDate = false;
        if (this.state.currentEndDate) await this.onFilter();
    }

    formatSendData(
        date_format,
        format_origin = "dd/MM/yyyy",
        format_final = "yyyy-MM-dd"
    ) {
        let formatDate = DateTime.fromFormat(date_format, format_origin);
        if (format_final) formatDate = formatDate.toFormat(format_final);
        return formatDate;
    }

    async onInputSearch(ev) {
        if (ev.key === "Enter") {
            await this.onFilter();
        }
    }

    /**
     * Retrieves the values of the filter inputs and calls the filter function
     * with them.
     *
     * @returns {Promise<void>}
     */
    async onFilter() {
        let startDate = null;
        let endDate = null;
        const val_search =
            this.inputSearch.el && this.inputSearch.el
                ? this.inputSearch.el.value
                : null;
        let chartFilterType = null;
        if (this.state.currentStartDate)
            startDate = this.formatSendData(this.state.currentStartDate);
        if (this.state.currentEndDate)
            endDate = this.formatSendData(this.state.currentEndDate);
        if (this.state.currentFilterType)
            chartFilterType = this.state.currentFilterType.id;
        await this.props.filter({
            id: this.props.objectId,
            startDate: startDate,
            endDate: endDate,
            val_search: val_search,
            chartFilterType: chartFilterType,
        });
    }
}
