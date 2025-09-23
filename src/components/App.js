import Component from "../core/Component.js";
import Items from "./Items.js";
import ItemAppender from "./ItemAppender.js";
import ItemFilter from "./ItemFilter.js";

export default class App extends Component {

    setup () {
        this._state = {
            isFilter: 0,
            items: [
                {
                    seq: 1,
                    contents: 'item1',
                    active: false,
                },
                {
                    seq: 2,
                    contents: 'item2',
                    active: true,
                },
            ],
        };
    }

    template () {
        return `
            <header data-component="item-appender"></header>
            <main data-component="items"></main>
            <footer data-component="item-filter"></footer>
        `;
    }

    mounted () {
        const { filteredItems, addItem, deleteItem, toggleItem, filterItem } = this;
        const _itemAppender = this._target.querySelector('[data-component="item-appender"]');
        const _items = this._target.querySelector('[data-component="items"]');
        const _itemFilter = this._target.querySelector('[data-component="item-filter"]');

        new ItemAppender(_itemAppender, {
            addItem: addItem.bind(this),
        });
        new Items(_items, {
            filteredItems,
            deleteItem: deleteItem.bind(this),
            toggleItem: toggleItem.bind(this),
        });
        new ItemFilter(_itemFilter, {
            filterItem: filterItem.bind(this),
        });
    }

    get filteredItems () {
        const { isFilter, items } = this._state;
        return items.filter(({ active }) => (isFilter === 1 && active) ||
        (isFilter === 2 && !active) ||
        isFilter === 0);
    }

    addItem (contents) {
        const {items} = this._state;
        const seq = Math.max(0, ...items.map(v => v.seq)) + 1;
        const active = false;
        this.setState({
            items: [
                ...items,
                {seq, contents, active},
            ],
        });
    }

    deleteItem (seq) {
        const items = [ ...this.$state.items ];
        items.splice(items.findIndex(v => v.seq === seq), 1);
        this.setState({items});
    }

    toggleItem (seq) {
        const items = [ ...this.$state.items ];
        const index = items.findIndex(v => v.seq === seq);
        items[index].active = !items[index].active;
        this.setState({items});
    }

    filterItem (isFilter) {
        this.setState({ isFilter });
    }
}