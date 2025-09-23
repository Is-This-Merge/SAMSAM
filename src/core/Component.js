export default class Component {
    _target;
    _properties;
    _state;
    constructor (_target, _properties) {
        this._target = _target;
        this._properties = _properties;
        this.setup();
        this.setEvent();
        this.render();
    }
    setup () {};
    mounted () {};
    template () { return ''; }
    render () {
        this._target.innerHTML = this.template();
        this.mounted();
    }
    setEvent () {}
    setState (newState) {
        this._state = { ...this._state, ...newState };
        this.render();
    }
    addEvent (eventType, selector, callback) {
        this._target.addEventListener(eventType, event => {
            if (!event.target.closest(selector)) return false;
            callback(event);
        });
    }
}
