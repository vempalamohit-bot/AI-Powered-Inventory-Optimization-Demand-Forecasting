import React, { useState } from 'react';
import { chatService } from '../services/api';

const ChatbotWidget = () => {
    const [messages, setMessages] = useState([
        {
            role: 'assistant',
            text: 'Hi! I\'m your Smart Inventory Assistant. Ask me about stock levels, top products, or overall inventory health.',
        },
    ]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [isOpen, setIsOpen] = useState(false);

    const sendMessage = async () => {
        const trimmed = input.trim();
        if (!trimmed || loading) return;

        const newMessages = [...messages, { role: 'user', text: trimmed }];
        setMessages(newMessages);
        setInput('');
        setLoading(true);

        try {
            const response = await chatService.ask(trimmed);
            setMessages([
                ...newMessages,
                {
                    role: 'assistant',
                    text: response.data.answer,
                },
            ]);
        } catch (error) {
            console.error('Error calling chat API:', error);
            setMessages([
                ...newMessages,
                {
                    role: 'assistant',
                    text: 'Sorry, I had trouble answering that. Please try again in a moment.',
                },
            ]);
        } finally {
            setLoading(false);
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    };

    return (
        <>
            <button
                className="chatbot-toggle"
                type="button"
                onClick={() => setIsOpen(!isOpen)}
                aria-label="Open Inventory Assistant"
            >
                <span className="chatbot-toggle-icon">💬</span>
            </button>

            {isOpen && (
                <div className="chatbot-widget">
                    <div className="chatbot-header">
                        <span>Smart Inventory Assistant</span>
                        <button
                            type="button"
                            className="chatbot-close"
                            onClick={() => setIsOpen(false)}
                        >
                            ✕
                        </button>
                    </div>
                    <div className="chatbot-body">
                        {messages.map((m, idx) => (
                            <div
                                key={idx}
                                className={`chatbot-message chatbot-message-${m.role}`}
                            >
                                {m.text.split('\n').map((line, i) => (
                                    <p key={i}>{line}</p>
                                ))}
                            </div>
                        ))}
                    </div>
                    <div className="chatbot-input">
                        <textarea
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder="Ask about stock, sales, or top products..."
                            rows={2}
                        />
                        <button
                            className="btn btn-primary"
                            onClick={sendMessage}
                            disabled={loading}
                        >
                            {loading ? 'Thinking...' : 'Ask'}
                        </button>
                    </div>
                </div>
            )}
        </>
    );
};

export default ChatbotWidget;
