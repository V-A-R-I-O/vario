import '@testing-library/jest-dom'

// jsdom doesn't implement Element.scrollTo — stub it so components that
// auto-scroll the chat thread can render under test.
if (typeof Element !== 'undefined' && !Element.prototype.scrollTo) {
  Element.prototype.scrollTo = () => {}
}
