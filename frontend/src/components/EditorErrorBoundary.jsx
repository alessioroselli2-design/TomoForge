import React from "react";
import {Link} from "react-router-dom";
export default class EditorErrorBoundary extends React.Component{
 state={failed:false};
 static getDerivedStateFromError(){return {failed:true};}
 render(){
  if(!this.state.failed)return this.props.children;
  return <main role="alert" className="min-h-screen bg-obsidian flex flex-col gap-4 items-center justify-center px-6 text-center">
   <h1 className="font-heading text-gold text-xl">L'editor ha incontrato un errore</h1>
   <p className="text-sm text-muted-foreground">Le carte già salvate non sono state modificate. Le modifiche non salvate potrebbero essere perse.</p>
   <button type="button" onClick={()=>this.setState({failed:false})} className="border border-gold px-4 py-2 text-gold">RIAPRI EDITOR</button>
   <Link to="/collezione" className="text-gold underline">Torna alla collezione</Link>
  </main>;
 }
}
