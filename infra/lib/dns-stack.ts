import * as cdk from "aws-cdk-lib";
import * as route53 from "aws-cdk-lib/aws-route53";
import * as acm from "aws-cdk-lib/aws-certificatemanager";
import { Construct } from "constructs";

export interface DnsStackProps extends cdk.StackProps {
  domainName: string;
  subdomain: string;
}

export class DnsStack extends cdk.Stack {
  public readonly hostedZone: route53.IHostedZone;
  public readonly certificate: acm.ICertificate;

  constructor(scope: Construct, id: string, props: DnsStackProps) {
    super(scope, id, props);

    const { domainName, subdomain } = props;
    const fullDomain = `${subdomain}.${domainName}`;

    // Look up existing hosted zone for getinsourced.ai
    this.hostedZone = route53.HostedZone.fromLookup(this, "HostedZone", {
      domainName: domainName,
    });

    // SSL certificate for subdomain
    this.certificate = new acm.Certificate(this, "Certificate", {
      domainName: fullDomain,
      validation: acm.CertificateValidation.fromDns(this.hostedZone),
    });

    // Outputs
    new cdk.CfnOutput(this, "CertificateArn", {
      value: this.certificate.certificateArn,
      description: "SSL Certificate ARN",
      exportName: "CoFounderCertArn",
    });

    new cdk.CfnOutput(this, "HostedZoneId", {
      value: this.hostedZone.hostedZoneId,
      description: "Hosted Zone ID",
      exportName: "CoFounderHostedZoneId",
    });
  }
}
