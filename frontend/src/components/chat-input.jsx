import { Textarea } from "./ui/textarea";

function ChatInput({ onChange, ...rest }) {
  function handleChange(e) {
    e.target.style.height = "auto";
    e.target.style.height = e.target.scrollHeight + "px";
    onChange?.(e);
  }

  return <Textarea onChange={handleChange} {...rest} />;
}

export { ChatInput };
