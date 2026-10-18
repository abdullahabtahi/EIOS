import React from "react";
import { FIELD_NOTES } from "./content";
import { NOTE_CHARTS } from "./data/charts";
import { MiniChart } from "./MiniChart";

export function FieldNotes() {
  return (
    <section id="field-notes" className="fde-notes" aria-labelledby="fde-notes-title">
      <h2 id="fde-notes-title" className="fde-h2" data-reveal>
        What the field taught us.
      </h2>
      <ol className="fde-note-list">
        {FIELD_NOTES.map((note) => (
          <li key={note.lead} data-reveal>
            <div className="fde-note-text">
              <h3>{note.lead}</h3>
              <p>{note.body}</p>
            </div>
            <div className="fde-note-figure">
              {NOTE_CHARTS[note.lead] && <MiniChart chart={NOTE_CHARTS[note.lead]} />}
              <dl className="fde-delta">
                <div>
                  <dt>Before</dt>
                  <dd>{note.before}</dd>
                </div>
                <div>
                  <dt>After</dt>
                  <dd className="fde-delta-after">
                    {note.after} <span className="fde-tag">MEASURED</span>
                  </dd>
                </div>
              </dl>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
