import Component from "../core/Component.js";

export default class ItemAppender extends Component {

    template() {
        return `<input type="text" class="appender" placeholder="아이템 내용 입력" />`;
    }

    setEvent() {
        const { addItem } = this._properties;
        this.addEvent('keyup', '.appender', ({ key, target }) => {
            if (key !== 'Enter') return;
            addItem(target.value);
        });
    }
}