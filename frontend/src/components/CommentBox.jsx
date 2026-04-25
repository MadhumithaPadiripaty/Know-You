import React, { useState, useEffect } from "react";
import axios from "axios";
// import "./comment.css";

const API = "http://localhost:8000";

export default function CommentBox() {
  const [username, setUsername] = useState("");
  const [comment, setComment] = useState("");
  const [comments, setComments] = useState([]);

  const loadComments = async () => {
    try {
      const res = await axios.get(`${API}/comments`);
      setComments(res.data.reverse());
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadComments();
  }, []);

  const submitComment = async (e) => {
    e.preventDefault();

    if (!username || !comment) return;

    const formData = new FormData();
    formData.append("username", username);
    formData.append("comment", comment);

    try {
      await axios.post(`${API}/comment`, formData);
      setUsername("");
      setComment("");
      loadComments();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="comment-container">
      <h3>💬 User Feedback</h3>

      <form onSubmit={submitComment} className="comment-form">
        <input
          type="text"
          placeholder="Your name"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />

        <textarea
          placeholder="Write your comment..."
          value={comment}
          onChange={(e) => setComment(e.target.value)}
        />

        <button type="submit">Post Comment</button>
      </form>

      <div className="comment-list">
        {comments.map((c, i) => (
          <div key={i} className="comment-item">
            <strong>{c.username}</strong>
            <p>{c.comment}</p>
          </div>
        ))}
      </div>
    </div>
  );
}  