export interface ConfirmationRequest {
  title:string;
  description:string;
  action:string;
  details?:string[];
  destructive?:boolean;
  allowed?:()=>boolean;
}

/** One shared modal; cancelling never runs an action or changes a draft. */
export class Confirmation {
  pending=$state.raw<ConfirmationRequest|null>(null);
  origin:HTMLElement|null=null;
  private resolve?: (confirmed:boolean)=>void;
  ask(request:ConfirmationRequest):Promise<boolean>{
    if(this.pending||request.allowed?.()===false)return Promise.resolve(false);
    this.origin=typeof document!=='undefined'&&document.activeElement instanceof HTMLElement?document.activeElement:null;
    return new Promise(resolve=>{this.resolve=resolve;this.pending=request;});
  }
  accept(){if(this.pending&&this.pending.allowed?.()!==false)this.finish(true);}
  cancel(){this.finish(false);}
  private finish(confirmed:boolean){const resolve=this.resolve;this.resolve=undefined;this.pending=null;resolve?.(confirmed);}
}
